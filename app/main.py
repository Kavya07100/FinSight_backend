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


# ============================================================
# Users
# ============================================================
@app.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = models.User(
        email=payload.email,
        hashed_password=f"unhashed:{payload.password}",
        full_name=payload.full_name,
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


# ============================================================
# Portfolio Service (rules-based risk scoring)
# ============================================================
@app.post("/users/{user_id}/risk-profile", response_model=schemas.RiskProfileOut, status_code=201)
def compute_and_store_risk_profile(
    user_id: uuid.UUID,
    payload: schemas.RiskProfileRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = compute_risk_profile(RiskProfileInput(
        income=payload.income,
        savings=payload.savings,
        goal=payload.goal,
        time_horizon_years=payload.time_horizon_years,
        pct_income_investable=payload.pct_income_investable,
        risk_tolerance_input=payload.risk_tolerance_input,
    ))

    latest_version = db.query(func.max(models.RiskProfile.version)).filter(
        models.RiskProfile.user_id == user_id
    ).scalar()
    next_version = (latest_version or 0) + 1

    profile = models.RiskProfile(
        user_id=user_id,
        version=next_version,
        income=payload.income,
        savings=payload.savings,
        goal=payload.goal,
        time_horizon_years=payload.time_horizon_years,
        pct_income_investable=payload.pct_income_investable,
        risk_tolerance_input=payload.risk_tolerance_input,
        risk_score=result.risk_score,
        category=result.category,
        score_breakdown=result.score_breakdown,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


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