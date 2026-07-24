import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models, schemas
from .database import get_db
from .portfolio_service import compute_risk_profile, RiskProfileInput
from .backtest_engine import Trade, run_backtest
from .price_data import get_price_data
from .learning_agent import generate_answer
from .behavior_engine import analyze_simulation
from .strategy_agent import generate_strategy

app = FastAPI(title="FinSight API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Onboarding doesn't collect these yet -- fixed placeholders until the
# frontend adds real inputs for them (see RiskProfileRequest docstring).
DEFAULT_TIME_HORIZON_YEARS = 10.0
DEFAULT_PCT_INCOME_INVESTABLE = 20.0

# Market Watch's tradable universe -- keep in sync with MARKET_STOCKS in
# finsight/app/simulate/page.tsx and TICKERS in scripts/ingest_prices.py.
COMPANY_NAMES = {
    "RELIANCE.NS": "Reliance Industries",
    "HDFCBANK.NS": "HDFC Bank",
    "INFY.NS": "Infosys",
    "TMPV.NS": "Tata Motors",
    "WIPRO.NS": "Wipro",
    "BAJFINANCE.NS": "Bajaj Finance",
    "NIFTYBEES.NS": "Nifty 50 ETF",
    "SBIN.NS": "State Bank of India",
    "SPY": "S&P 500 ETF",
}


def _get_latest_price(db: Session, ticker: str) -> float | None:
    latest = (
        db.query(models.PriceHistory)
        .filter(models.PriceHistory.ticker == ticker)
        .order_by(models.PriceHistory.date.desc())
        .first()
    )
    return float(latest.close) if latest else None


def _record_transaction_and_update_holding(
    db: Session,
    user_id: uuid.UUID,
    ticker: str,
    action: str,
    quantity: int,
    trade_date,
) -> None:
    """
    Called once per trade after a sandbox simulation succeeds. Records a
    Transaction and upserts portfolio_holdings. Uses the LATEST close price
    in price_history (not the historical price on trade_date) as the
    recorded transaction price, per spec -- the simulation itself already
    used the historical price for its own math; this is what the Portfolio
    page shows as "what you'd pay/receive if you did this trade today."
    """
    price = _get_latest_price(db, ticker)
    if price is None:
        return  # no price data at all for this ticker -- nothing to record against

    company_name = COMPANY_NAMES.get(ticker, ticker)

    db.add(models.Transaction(
        user_id=user_id,
        ticker=ticker,
        company_name=company_name,
        action=action,
        quantity=quantity,
        price=price,
        total_value=price * quantity,
        trade_date=trade_date,
    ))

    holding = (
        db.query(models.PortfolioHolding)
        .filter(
            models.PortfolioHolding.user_id == user_id,
            models.PortfolioHolding.ticker == ticker,
        )
        .first()
    )

    if action == "buy":
        if holding:
            new_quantity = holding.quantity + quantity
            holding.avg_buy_price = (
                (float(holding.avg_buy_price) * holding.quantity) + (price * quantity)
            ) / new_quantity
            holding.quantity = new_quantity
        else:
            db.add(models.PortfolioHolding(
                user_id=user_id,
                ticker=ticker,
                company_name=company_name,
                quantity=quantity,
                avg_buy_price=price,
            ))
    elif action == "sell" and holding:
        remaining = holding.quantity - quantity
        if remaining <= 0:
            db.delete(holding)  # fully closed (or oversold) -- drop the position
        else:
            holding.quantity = remaining
    # else: selling a ticker with no existing holding -- transaction is
    # still recorded above, but there's no position to reduce.

    db.commit()


# ============================================================
# Users
# ============================================================
@app.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    # Onboarding doesn't collect email/password (no real auth yet), so
    # generate placeholders to satisfy the users table's NOT NULL/unique
    # constraints. Matches the existing "unhashed:" placeholder scheme --
    # not real auth either way.
    user = models.User(
        email=f"{uuid.uuid4()}@onboarding.local",
        hashed_password=f"unhashed:{uuid.uuid4()}",
        full_name=payload.full_name,
        age=payload.age,
        monthly_income=payload.monthly_income,
        current_savings=payload.current_savings,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: uuid.UUID,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.age is not None:
        user.age = payload.age
    if payload.monthly_income is not None:
        user.monthly_income = payload.monthly_income
    if payload.current_savings is not None:
        user.current_savings = payload.current_savings

    db.add(user)
    db.commit()
    db.refresh(user)

    if payload.investment_goal is not None or payload.risk_tolerance is not None:
        latest_profile = (
            db.query(models.RiskProfile)
            .filter(models.RiskProfile.user_id == user_id)
            .order_by(models.RiskProfile.version.desc())
            .first()
        )

        resolved_goal = (
            payload.investment_goal if payload.investment_goal is not None
            else (latest_profile.goal if latest_profile else None)
        )
        resolved_risk_tolerance = (
            payload.risk_tolerance if payload.risk_tolerance is not None
            else (latest_profile.risk_tolerance_input if latest_profile else None)
        )

        if (
            user.age is None or user.monthly_income is None or user.current_savings is None
            or resolved_goal is None or resolved_risk_tolerance is None
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "age, monthly_income, current_savings, investment_goal, and "
                    "risk_tolerance must all be set (either already on the user, "
                    "from a prior risk profile, or in this request) to recompute "
                    "a risk profile."
                ),
            )

        _create_risk_profile_version(
            db,
            user_id,
            schemas.RiskProfileRequest(
                age=user.age,
                monthly_income=float(user.monthly_income),
                current_savings=float(user.current_savings),
                investment_goal=resolved_goal,
                risk_tolerance=resolved_risk_tolerance,
            ),
        )

    return user


# ============================================================
# Portfolio Service (rules-based risk scoring)
# ============================================================
def _create_risk_profile_version(
    db: Session, user_id: uuid.UUID, payload: schemas.RiskProfileRequest
) -> models.RiskProfile:
    """
    Shared by POST /users/{user_id}/risk-profile and PUT /users/{user_id}
    (the latter re-scores whenever investment_goal or risk_tolerance changes).
    Caller is responsible for confirming the user exists first.
    """
    annual_income = payload.monthly_income * 12

    result = compute_risk_profile(RiskProfileInput(
        income=annual_income,
        savings=payload.current_savings,
        goal=payload.investment_goal,
        time_horizon_years=DEFAULT_TIME_HORIZON_YEARS,
        pct_income_investable=DEFAULT_PCT_INCOME_INVESTABLE,
        risk_tolerance_input=payload.risk_tolerance,
    ))

    latest_version = db.query(func.max(models.RiskProfile.version)).filter(
        models.RiskProfile.user_id == user_id
    ).scalar()
    next_version = (latest_version or 0) + 1

    profile = models.RiskProfile(
        user_id=user_id,
        version=next_version,
        income=annual_income,
        savings=payload.current_savings,
        goal=payload.investment_goal,
        time_horizon_years=DEFAULT_TIME_HORIZON_YEARS,
        pct_income_investable=DEFAULT_PCT_INCOME_INVESTABLE,
        risk_tolerance_input=payload.risk_tolerance,
        risk_score=result.risk_score,
        category=result.category,
        score_breakdown=result.score_breakdown,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@app.post("/users/{user_id}/risk-profile", response_model=schemas.RiskProfileOut, status_code=201)
def compute_and_store_risk_profile(
    user_id: uuid.UUID,
    payload: schemas.RiskProfileRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return _create_risk_profile_version(db, user_id, payload)


@app.get("/users/{user_id}/risk-profile", response_model=schemas.RiskProfileOut)
def get_latest_risk_profile(user_id: uuid.UUID, db: Session = Depends(get_db)):
    profile = (
        db.query(models.RiskProfile)
        .filter(models.RiskProfile.user_id == user_id)
        .order_by(models.RiskProfile.version.desc())
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="No risk profile computed yet")
    return profile


@app.get("/users/{user_id}/risk-profile/history", response_model=list[schemas.RiskProfileOut])
def get_risk_profile_history(user_id: uuid.UUID, db: Session = Depends(get_db)):
    profiles = (
        db.query(models.RiskProfile)
        .filter(models.RiskProfile.user_id == user_id)
        .order_by(models.RiskProfile.version.asc())
        .all()
    )
    return profiles


# ============================================================
# Simulation Environment (sandbox mode)
# ============================================================
@app.post(
    "/users/{user_id}/simulate/sandbox",
    response_model=schemas.SimulationResultOut,
    status_code=201,
)
def run_sandbox_simulation(
    user_id: uuid.UUID,
    payload: schemas.SandboxSimulationRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prices = get_price_data(payload.tickers, payload.start_date, payload.end_date)
    if not prices:
        raise HTTPException(
            status_code=400,
            detail="No price data found for the given tickers/date range",
        )

    trades = [
        Trade(ticker=t.ticker, action=t.action, quantity=t.quantity, trade_date=t.trade_date)
        for t in payload.trades
    ]

    result = run_backtest(trades, prices, payload.starting_cash)

    benchmark_metrics = None
    benchmark_prices = get_price_data(
        [payload.benchmark_ticker], payload.start_date, payload.end_date
    )
    if benchmark_prices:
        first_day = benchmark_prices[0]
        shares = int(payload.starting_cash // first_day.close)
        if shares > 0:
            benchmark_trade = [
                Trade(
                    ticker=payload.benchmark_ticker,
                    action="buy",
                    quantity=shares,
                    trade_date=first_day.trade_date,
                )
            ]
            benchmark_result = run_backtest(
                benchmark_trade, benchmark_prices, payload.starting_cash
            )
            benchmark_metrics = {
                "ticker": payload.benchmark_ticker,
                "final_value": benchmark_result["final_value"],
                "total_return_pct": benchmark_result["total_return_pct"],
            }

    trades_json = [
        {
            "ticker": t.ticker,
            "action": t.action,
            "quantity": t.quantity,
            "trade_date": t.trade_date.isoformat(),
        }
        for t in payload.trades
    ]
    metrics_json = {
        "final_value": result["final_value"],
        "total_return_pct": result["total_return_pct"],
        "max_drawdown_pct": result["max_drawdown_pct"],
        "daily_values": [
            {"date": row["date"].isoformat(), "value": row["value"]}
            for row in result["daily_values"]
        ],
        "benchmark": benchmark_metrics,
        "outperformance_pct": (
            result["total_return_pct"] - benchmark_metrics["total_return_pct"]
            if benchmark_metrics else None
        ),
    }

    log = models.SimulationLog(
        user_id=user_id,
        strategy_config_id=None,
        mode="sandbox",
        trades=trades_json,
        metrics=metrics_json,
        ended_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    for t in payload.trades:
        _record_transaction_and_update_holding(
            db, user_id, t.ticker, t.action, t.quantity, t.trade_date
        )

    return log


# ============================================================
# Behavior Engine
# ============================================================
@app.post(
    "/users/{user_id}/simulate/{log_id}/analyze",
    response_model=schemas.BehaviorAnalysisOut,
)
def analyze_simulation_behavior(
    user_id: uuid.UUID,
    log_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Analyzes a completed simulation session's trading behavior.
    Computes behavioral metrics (panic sell rate, trade frequency,
    diversification etc.) and generates LLM feedback.
    Writes results back into simulation_logs.metrics under a "behavior" key.
    """
    log = db.query(models.SimulationLog).filter(
        models.SimulationLog.id == log_id,
        models.SimulationLog.user_id == user_id,
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Simulation log not found")

    profile = (
        db.query(models.RiskProfile)
        .filter(models.RiskProfile.user_id == user_id)
        .order_by(models.RiskProfile.version.desc())
        .first()
    )
    risk_category = profile.category if profile else "moderate"

    result = analyze_simulation(
        trades=log.trades,
        metrics=log.metrics or {},
        risk_category=risk_category,
    )

    updated_metrics = {**(log.metrics or {}), **result}

    log.metrics = updated_metrics
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ============================================================
# Portfolio Engine
# ============================================================
@app.get("/users/{user_id}/portfolio", response_model=schemas.PortfolioOut)
def get_portfolio(user_id: uuid.UUID, db: Session = Depends(get_db)):
    holdings = (
        db.query(models.PortfolioHolding)
        .filter(models.PortfolioHolding.user_id == user_id)
        .all()
    )

    holdings_out = []
    total_value = 0.0
    total_invested = 0.0
    today_pnl = 0.0

    for h in holdings:
        # Latest close = current_price; the one before it = "yesterday's"
        # close, used to derive today_pnl (not specified explicitly in the
        # spec's formula list, so defined here as the mark-to-market move
        # since the previous available trading day).
        recent_prices = (
            db.query(models.PriceHistory)
            .filter(models.PriceHistory.ticker == h.ticker)
            .order_by(models.PriceHistory.date.desc())
            .limit(2)
            .all()
        )
        avg_buy_price = float(h.avg_buy_price)
        current_price = float(recent_prices[0].close) if recent_prices else avg_buy_price
        previous_price = float(recent_prices[1].close) if len(recent_prices) > 1 else current_price

        current_value = h.quantity * current_price
        invested = h.quantity * avg_buy_price
        pnl_pct = ((current_price - avg_buy_price) / avg_buy_price) * 100 if avg_buy_price else 0.0

        holdings_out.append(schemas.HoldingOut(
            id=h.id,
            ticker=h.ticker,
            company_name=h.company_name,
            quantity=h.quantity,
            avg_buy_price=avg_buy_price,
            current_price=current_price,
            current_value=current_value,
            pnl_pct=pnl_pct,
        ))

        total_value += current_value
        total_invested += invested
        today_pnl += h.quantity * (current_price - previous_price)

    overall_return_pct = (
        ((total_value - total_invested) / total_invested) * 100 if total_invested else 0.0
    )

    return schemas.PortfolioOut(
        holdings=holdings_out,
        total_value=total_value,
        total_invested=total_invested,
        overall_return_pct=overall_return_pct,
        today_pnl=today_pnl,
    )


@app.get("/users/{user_id}/transactions", response_model=list[schemas.TransactionOut])
def get_transactions(user_id: uuid.UUID, db: Session = Depends(get_db)):
    return (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == user_id)
        .order_by(models.Transaction.created_at.desc())
        .limit(10)
        .all()
    )


@app.get("/users/{user_id}/simulations/latest", response_model=schemas.SimulationResultOut)
def get_latest_simulation(user_id: uuid.UUID, db: Session = Depends(get_db)):
    log = (
        db.query(models.SimulationLog)
        .filter(models.SimulationLog.user_id == user_id)
        .order_by(models.SimulationLog.started_at.desc())
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="No simulations found for this user")
    return log


# ============================================================
# Learning Agent (RAG)
# ============================================================
@app.post("/learning/ask", response_model=schemas.LearningAskResponse)
def ask_learning_agent(payload: schemas.LearningAskRequest):
    result = generate_answer(payload.question)
    return schemas.LearningAskResponse(answer=result["answer"], sources=result["sources"])


# ============================================================
# Strategy Agent
# ============================================================
@app.post("/users/{user_id}/strategy", response_model=schemas.StrategyConfigOut, status_code=201)
def generate_and_store_strategy(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Generates a new learning path for the user using their latest risk profile.
    Stores it as a new version in strategy_configs (never overwrites old ones).
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = (
        db.query(models.RiskProfile)
        .filter(models.RiskProfile.user_id == user_id)
        .order_by(models.RiskProfile.version.desc())
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="No risk profile found. Complete onboarding first.",
        )

    risk_profile_dict = {
        "risk_score": profile.risk_score,
        "category": profile.category,
        "goal": profile.goal,
        "time_horizon_years": float(profile.time_horizon_years),
        "pct_income_investable": float(profile.pct_income_investable),
        "risk_tolerance_input": profile.risk_tolerance_input,
        "score_breakdown": profile.score_breakdown,
    }

    # Look up most recent behavior scores from simulation logs
    latest_log = (
        db.query(models.SimulationLog)
        .filter(
            models.SimulationLog.user_id == user_id,
            models.SimulationLog.metrics.isnot(None),
        )
        .order_by(models.SimulationLog.started_at.desc())
        .first()
    )
    behavior_score = (
        latest_log.metrics.get("behavior") if latest_log and latest_log.metrics else None
    )

    path = generate_strategy(risk_profile_dict, behavior_score=behavior_score)

    latest_version = db.query(func.max(models.StrategyConfig.version)).filter(
        models.StrategyConfig.user_id == user_id
    ).scalar()
    next_version = (latest_version or 0) + 1

    config = models.StrategyConfig(
        user_id=user_id,
        version=next_version,
        risk_profile_id=profile.id,
        path=path,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@app.get("/users/{user_id}/strategy", response_model=schemas.StrategyConfigOut)
def get_latest_strategy(user_id: uuid.UUID, db: Session = Depends(get_db)):
    config = (
        db.query(models.StrategyConfig)
        .filter(models.StrategyConfig.user_id == user_id)
        .order_by(models.StrategyConfig.version.desc())
        .first()
    )
    if not config:
        raise HTTPException(status_code=404, detail="No strategy generated yet")
    return config