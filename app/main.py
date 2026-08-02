import random
import re
import time
import uuid
import yfinance as yf
from datetime import date, datetime, timezone
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
    # TEMPORARY: Starlette's CORSMiddleware matches allow_origins by exact
    # string equality (no glob support) -- "https://*.vercel.app" there
    # would never match a real origin and silently block everything. This
    # regex is the actual mechanism for pattern-matching origins. Since
    # vercel.app is a shared multi-tenant domain, this allows ANY project
    # hosted there (not just ours) to make credentialed requests -- replace
    # with the exact frontend origin once it's known.
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Market Watch's tradable list on the simulate page -- 8 tickers, no SPY
# (SPY is only used as the backtest benchmark, never shown/tradable here).
MARKET_WATCH_TICKERS = [
    "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TMPV.NS",
    "WIPRO.NS", "BAJFINANCE.NS", "NIFTYBEES.NS", "SBIN.NS",
]

# Simple in-process cache -- Yahoo Finance rate-limits/blocks callers that
# hit it on every page load, and Market Watch is read by every user viewing
# the simulate page. A module-level dict is enough here since this is a
# single-process dev/demo deployment (no shared cache across workers).
MARKET_PRICES_CACHE_TTL_SECONDS = 300
_market_prices_cache: dict = {"data": {}, "fetched_at": 0.0}


@app.get("/market/prices")
def get_market_prices():
    now = time.time()
    cached = _market_prices_cache["data"]
    if cached and now - _market_prices_cache["fetched_at"] < MARKET_PRICES_CACHE_TTL_SECONDS:
        return cached

    fresh = {}
    try:
        df = yf.download(MARKET_WATCH_TICKERS, period="2d", interval="1d", progress=False)
        for ticker in MARKET_WATCH_TICKERS:
            try:
                closes = df["Close"][ticker].dropna()
                if len(closes) < 2:
                    continue
                today_close = float(closes.iloc[-1])
                yesterday_close = float(closes.iloc[-2])
                change_pct = (today_close - yesterday_close) / yesterday_close * 100
                fresh[ticker] = {
                    "name": COMPANY_NAMES[ticker],
                    "price": round(today_close, 2),
                    "change_pct": round(change_pct, 2),
                }
            except Exception:
                # This ticker's columns were missing/unusable -- fall through
                # to the cached-value-or-skip merge below.
                continue
    except Exception:
        # Whole batch call failed (e.g. network down) -- fresh stays empty,
        # merge below falls back to cache for every ticker.
        pass

    # Per-ticker fallback: prefer freshly fetched data, else last cached
    # value for that ticker, else omit it entirely.
    merged = {}
    for ticker in MARKET_WATCH_TICKERS:
        if ticker in fresh:
            merged[ticker] = fresh[ticker]
        elif ticker in cached:
            merged[ticker] = cached[ticker]

    _market_prices_cache["data"] = merged
    _market_prices_cache["fetched_at"] = now
    return merged


# Static scenario definitions -- each maps to a real historical Indian market
# period with price_history data already ingested for it, so the sandbox
# simulator can run against it unmodified (it just needs a start_date/end_date).
MARKET_SCENARIOS = [
    {
        "id": "easy",
        "name": "Bull Market Rally",
        "difficulty": "Easy",
        "description": "Practice in a rising market — the 2023 Indian market recovery",
        "context": "Post-COVID recovery drove strong FII inflows into Indian markets. Sensex rose from 60,000 to 72,000 (+20%). Most stocks trended upward consistently.",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "hint": "Markets generally rising — test basic buy-and-hold strategies",
        "color": "green",
    },
    {
        "id": "medium",
        "name": "Mixed Market",
        "difficulty": "Medium",
        "description": "Realistic conditions — the 2024 Indian market",
        "context": "India's market showed selective growth in 2024. Large caps outperformed mid-caps. Sector rotation created both opportunities and traps.",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "hint": "Mixed conditions — stock selection matters more than market timing",
        "color": "yellow",
    },
    {
        "id": "hard",
        "name": "Market Correction",
        "difficulty": "Hard",
        "description": "Navigate a downturn — the early 2022 correction",
        "context": "Global inflation hit 40-year highs. The US Federal Reserve began aggressive rate hikes. FIIs pulled billions from emerging markets including India. Sensex fell 15% in 6 months.",
        "start_date": "2022-01-01",
        "end_date": "2022-06-30",
        "hint": "Markets falling — can you avoid panic selling and find opportunities?",
        "color": "red",
    },
    {
        "id": "expert",
        "name": "High Volatility",
        "difficulty": "Expert",
        "description": "Rapid swings — the volatile second half of 2022",
        "context": "After the correction, markets oscillated wildly. Some sectors recovered sharply while others continued falling. Timing and discipline were critical.",
        "start_date": "2022-07-01",
        "end_date": "2022-12-31",
        "hint": "Unpredictable swings — test sophisticated strategies and emotional discipline",
        "color": "purple",
    },
]


@app.get("/market/scenarios")
def get_market_scenarios():
    return MARKET_SCENARIOS


# Mirrors each scenario's start_date/end_date from MARKET_SCENARIOS, keyed
# for quick lookup by scenario portfolio endpoints (pricing holdings as of
# the scenario's end date rather than today for historical scenarios).
SCENARIO_DATE_RANGES = {
    "easy": {"start": "2023-01-01", "end": "2023-12-31"},
    "medium": {"start": "2024-01-01", "end": "2024-12-31"},
    "hard": {"start": "2022-01-01", "end": "2022-06-30"},
    "expert": {"start": "2022-07-01", "end": "2022-12-31"},
    "live": None,
}

# Challenge Mode: day-by-day blind historical simulation. "days" caps how
# many trading days the session runs for -- each window is wider than that
# (see the "start"/"end" bounds) so there's always more than enough real
# trading days to pick the first N from, regardless of holidays.
CHALLENGE_SCENARIOS = [
    # Easy difficulty -- bull markets
    {
        "id": "bull_2023", "difficulty": "easy", "start": "2023-01-02", "end": "2023-06-30", "days": 60,
        "context": "India's post-COVID recovery continued into 2023, with strong FII inflows and resilient corporate earnings driving a steady rally through the first half of the year.",
    },
    {
        "id": "bull_2024", "difficulty": "easy", "start": "2024-01-02", "end": "2024-06-30", "days": 60,
        "context": "Indian markets extended their multi-year rally into 2024, hitting fresh record highs, though a sharp swing followed the general election results in early June before markets steadied.",
    },

    # Medium difficulty -- mixed markets
    {
        "id": "mixed_2023h2", "difficulty": "medium", "start": "2023-07-01", "end": "2023-12-31", "days": 60,
        "context": "India's market showed selective growth in the second half of 2023 -- large caps outperformed mid-caps, and sector rotation created both opportunities and traps.",
    },
    {
        "id": "mixed_2024h2", "difficulty": "medium", "start": "2024-07-01", "end": "2024-12-31", "days": 60,
        "context": "Markets pulled back sharply from record highs in late 2024 as heavy foreign investor selling took hold, with large caps and mid-caps diverging through the final months of the year.",
    },

    # Hard difficulty -- corrections
    {
        "id": "crash_2022h1", "difficulty": "hard", "start": "2022-01-03", "end": "2022-06-30", "days": 60,
        "context": "Global inflation hit 40-year highs. The US Federal Reserve began aggressive rate hikes. FIIs pulled billions from emerging markets including India. The Sensex fell sharply through the first half of 2022.",
    },
    {
        "id": "crash_2022h2", "difficulty": "hard", "start": "2022-07-01", "end": "2022-12-30", "days": 60,
        "context": "Markets stabilized and staged a strong recovery in the second half of 2022 as the earlier correction eased, though global rate-hike uncertainty kept volatility elevated.",
    },

    # Expert -- high volatility mixed
    {
        "id": "volatile_2022q1", "difficulty": "expert", "start": "2022-01-03", "end": "2022-03-31", "days": 40,
        "context": "Markets swung sharply in early 2022 as Russia's invasion of Ukraine in late February spiked crude oil prices and global risk-off sentiment, layering fresh volatility on top of already-rising inflation fears.",
    },
    {
        "id": "volatile_2024q4", "difficulty": "expert", "start": "2024-10-01", "end": "2024-12-31", "days": 40,
        "context": "Markets swung wildly in the final quarter of 2024, with heavy FII selling triggering a sharp correction from record highs before volatility persisted into year-end amid mixed earnings and global cues.",
    },
]


@app.get("/market/historical-prices")
def get_historical_prices(start_date: date, end_date: date, db: Session = Depends(get_db)):
    """
    Same shape as GET /market/prices, but for a historical scenario window:
    "price" is the close on/just after start_date (what you'd have paid
    entering the position), and "change_pct" is the *period* return through
    to the close on/just before end_date -- not a single day's move.
    """
    if start_date.year == end_date.year:
        period_label = f"{start_date:%b}-{end_date:%b %Y}"
    else:
        period_label = f"{start_date:%b %Y}-{end_date:%b %Y}"

    result = {}
    for ticker in MARKET_WATCH_TICKERS:
        start_row = (
            db.query(models.PriceHistory)
            .filter(models.PriceHistory.ticker == ticker, models.PriceHistory.date >= start_date)
            .order_by(models.PriceHistory.date.asc())
            .first()
        )
        end_row = (
            db.query(models.PriceHistory)
            .filter(models.PriceHistory.ticker == ticker, models.PriceHistory.date <= end_date)
            .order_by(models.PriceHistory.date.desc())
            .first()
        )
        if not start_row or not end_row:
            continue

        start_price = float(start_row.close)
        end_price = float(end_row.close)
        period_return_pct = (end_price - start_price) / start_price * 100 if start_price else 0.0

        result[ticker] = {
            "name": COMPANY_NAMES[ticker],
            "price": round(start_price, 2),
            "change_pct": round(period_return_pct, 2),
            "period": period_label,
        }
    return result


def _get_latest_price(db: Session, ticker: str, as_of: date | None = None) -> float | None:
    """
    Without as_of: latest known close for the ticker.
    With as_of: closest available close on or before that date (the nearest
    trading day at/before it, since as_of itself may be a weekend/holiday
    with no row) -- used to price a transaction at its actual trade_date
    instead of today's price.
    """
    query = db.query(models.PriceHistory).filter(models.PriceHistory.ticker == ticker)
    if as_of is not None:
        query = query.filter(models.PriceHistory.date <= as_of)
    latest = query.order_by(models.PriceHistory.date.desc()).first()
    return float(latest.close) if latest else None


def _record_transaction_and_update_holding(
    db: Session,
    user_id: uuid.UUID,
    ticker: str,
    action: str,
    quantity: int,
    trade_date,
    scenario_id: str = "live",
) -> None:
    """
    Called once per trade after a sandbox simulation succeeds. Records a
    Transaction and upserts portfolio_holdings, priced at the actual close
    on trade_date (nearest available trading day at/before it) -- not
    today's price. Using today's price for both the buy price AND the
    current price would make every position's P&L trivially 0%.

    scenario_id isolates holdings/transactions per scenario -- the same
    ticker can be held independently in "live" and in each historical
    scenario without them affecting each other (see portfolio_holdings'
    UNIQUE(user_id, ticker, scenario_id)).
    """
    price = _get_latest_price(db, ticker, as_of=trade_date)
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
        scenario_id=scenario_id,
    ))

    holding = (
        db.query(models.PortfolioHolding)
        .filter(
            models.PortfolioHolding.user_id == user_id,
            models.PortfolioHolding.ticker == ticker,
            models.PortfolioHolding.scenario_id == scenario_id,
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
                scenario_id=scenario_id,
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


def _get_or_create_scenario_portfolio(
    db: Session, user_id: uuid.UUID, scenario_id: str
) -> models.ScenarioPortfolio:
    portfolio = (
        db.query(models.ScenarioPortfolio)
        .filter(
            models.ScenarioPortfolio.user_id == user_id,
            models.ScenarioPortfolio.scenario_id == scenario_id,
        )
        .first()
    )
    if not portfolio:
        portfolio = models.ScenarioPortfolio(
            user_id=user_id,
            scenario_id=scenario_id,
            starting_balance=100000,
            virtual_cash=100000,
            is_started=False,
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
    return portfolio


def _build_scenario_holdings(
    db: Session, user_id: uuid.UUID, scenario_id: str
) -> tuple[list[schemas.HoldingOut], float, float]:
    """
    Same P&L math as GET /users/{user_id}/portfolio, but scoped to one
    scenario's holdings and priced as of that scenario's end date for
    historical scenarios (there's no "today's price" for a 2022 backtest --
    the last trading day it ran through is the right mark).
    """
    date_range = SCENARIO_DATE_RANGES.get(scenario_id)
    as_of = date.fromisoformat(date_range["end"]) if date_range else None

    holdings = (
        db.query(models.PortfolioHolding)
        .filter(
            models.PortfolioHolding.user_id == user_id,
            models.PortfolioHolding.scenario_id == scenario_id,
        )
        .all()
    )

    holdings_out = []
    total_value = 0.0
    total_invested = 0.0

    for h in holdings:
        avg_buy_price = float(h.avg_buy_price)
        current_price = _get_latest_price(db, h.ticker, as_of=as_of) or avg_buy_price
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

    overall_return_pct = (
        ((total_value - total_invested) / total_invested) * 100 if total_invested else 0.0
    )
    return holdings_out, total_invested, overall_return_pct


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
        dependents=payload.dependents,
        employment_type=payload.employment_type,
        existing_investments=payload.existing_investments,
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
        # PUT /users/{id} only ever changes investment_goal/risk_tolerance
        # (see settings/page.tsx) -- time_horizon_years/pct_income_investable
        # aren't collected here, so carry over whatever the last computed
        # risk profile used.
        resolved_time_horizon = latest_profile.time_horizon_years if latest_profile else None
        resolved_pct_investable = latest_profile.pct_income_investable if latest_profile else None

        if (
            user.age is None or user.monthly_income is None or user.current_savings is None
            or resolved_goal is None or resolved_risk_tolerance is None
            or resolved_time_horizon is None or resolved_pct_investable is None
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
                time_horizon_years=float(resolved_time_horizon),
                pct_income_investable=float(resolved_pct_investable),
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
        time_horizon_years=payload.time_horizon_years,
        pct_income_investable=payload.pct_income_investable,
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
        time_horizon_years=payload.time_horizon_years,
        pct_income_investable=payload.pct_income_investable,
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
        "executed_trades": [
            {
                "ticker": t["ticker"],
                "action": t["action"],
                "quantity": t["quantity"],
                "trade_date": t["trade_date"].isoformat(),
                "price": t["price"],
                "cost": t["cost"],
            }
            for t in result["executed_trades"]
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
            db, user_id, t.ticker, t.action, t.quantity, t.trade_date,
            scenario_id=payload.scenario_id,
        )

    # Deduct this run's net cash outflow from the scenario's virtual_cash --
    # executed_trades' "cost" is always a positive price*quantity magnitude,
    # so buys subtract and sells add back.
    scenario_portfolio = _get_or_create_scenario_portfolio(db, user_id, payload.scenario_id)
    net_cash_spent = sum(
        t["cost"] if t["action"] == "buy" else -t["cost"]
        for t in result["executed_trades"]
    )
    scenario_portfolio.virtual_cash = float(scenario_portfolio.virtual_cash) - net_cash_spent
    scenario_portfolio.is_started = True
    db.commit()

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
    # This endpoint predates scenario portfolios and represents the "live"
    # scenario specifically -- scoped so historical-scenario practice trades
    # never bleed into the main dashboard/portfolio views.
    holdings = (
        db.query(models.PortfolioHolding)
        .filter(
            models.PortfolioHolding.user_id == user_id,
            models.PortfolioHolding.scenario_id == "live",
        )
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
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.scenario_id == "live",
        )
        .order_by(models.Transaction.created_at.desc())
        .limit(10)
        .all()
    )


@app.post("/users/{user_id}/reset-portfolio")
def reset_portfolio(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.query(models.PortfolioHolding).filter(
        models.PortfolioHolding.user_id == user_id,
        models.PortfolioHolding.scenario_id == "live",
    ).delete()
    db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.scenario_id == "live",
    ).delete()
    db.query(models.SimulationLog).filter(models.SimulationLog.user_id == user_id).delete()

    live_portfolio = (
        db.query(models.ScenarioPortfolio)
        .filter(
            models.ScenarioPortfolio.user_id == user_id,
            models.ScenarioPortfolio.scenario_id == "live",
        )
        .first()
    )
    if live_portfolio:
        live_portfolio.virtual_cash = live_portfolio.starting_balance
        live_portfolio.is_started = False

    db.commit()

    return {"message": "Portfolio reset successfully"}


# ============================================================
# Scenario Portfolios (per-scenario cash + holdings isolation)
# ============================================================
@app.get(
    "/users/{user_id}/scenario/{scenario_id}/portfolio",
    response_model=schemas.ScenarioPortfolioOut,
)
def get_scenario_portfolio(user_id: uuid.UUID, scenario_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    portfolio = _get_or_create_scenario_portfolio(db, user_id, scenario_id)
    holdings_out, total_invested, overall_return_pct = _build_scenario_holdings(
        db, user_id, scenario_id
    )

    return schemas.ScenarioPortfolioOut(
        scenario_id=scenario_id,
        virtual_cash=float(portfolio.virtual_cash),
        starting_balance=float(portfolio.starting_balance),
        is_started=portfolio.is_started,
        total_invested=total_invested,
        holdings=holdings_out,
        overall_return_pct=overall_return_pct,
    )


@app.post(
    "/users/{user_id}/scenario/{scenario_id}/set-balance",
    response_model=schemas.ScenarioPortfolioOut,
)
def set_scenario_balance(
    user_id: uuid.UUID,
    scenario_id: str,
    payload: schemas.SetScenarioBalanceRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    portfolio = _get_or_create_scenario_portfolio(db, user_id, scenario_id)
    if portfolio.is_started:
        raise HTTPException(
            status_code=400, detail="Cannot change balance after trading has begun"
        )

    portfolio.starting_balance = payload.starting_balance
    portfolio.virtual_cash = payload.starting_balance
    db.commit()
    db.refresh(portfolio)

    holdings_out, total_invested, overall_return_pct = _build_scenario_holdings(
        db, user_id, scenario_id
    )
    return schemas.ScenarioPortfolioOut(
        scenario_id=scenario_id,
        virtual_cash=float(portfolio.virtual_cash),
        starting_balance=float(portfolio.starting_balance),
        is_started=portfolio.is_started,
        total_invested=total_invested,
        holdings=holdings_out,
        overall_return_pct=overall_return_pct,
    )


@app.post(
    "/users/{user_id}/scenario/{scenario_id}/reset",
    response_model=schemas.ScenarioResetOut,
)
def reset_scenario_portfolio(user_id: uuid.UUID, scenario_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    portfolio = _get_or_create_scenario_portfolio(db, user_id, scenario_id)

    db.query(models.PortfolioHolding).filter(
        models.PortfolioHolding.user_id == user_id,
        models.PortfolioHolding.scenario_id == scenario_id,
    ).delete()
    db.query(models.Transaction).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.scenario_id == scenario_id,
    ).delete()

    portfolio.virtual_cash = portfolio.starting_balance
    portfolio.is_started = False
    db.commit()

    return schemas.ScenarioResetOut(
        message="Scenario reset", virtual_cash=float(portfolio.virtual_cash)
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
    behavior_data = (
        latest_log.metrics.get("behavior", {}) if latest_log and latest_log.metrics else {}
    )
    # Key is overall_behavior_score, not behavior_score -- see
    # behavior_engine.py's compute_behavior_metrics return shape.
    behavior_score = behavior_data.get("overall_behavior_score")
    behavior_flags = behavior_data.get("flags", [])

    path = generate_strategy(
        risk_profile_dict,
        behavior_score=behavior_score,
        behavior_flags=behavior_flags,
        score_breakdown=profile.score_breakdown or {},
    )

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


# news_agent.py stores articles as a single `content` string ending in
# "(Source: <name>. Read more: <url>)" -- see build_content() there. This
# pulls those two pieces back out so the API can return structured fields
# instead of making the frontend regex the text itself.
NEWS_SOURCE_PATTERN = re.compile(
    r"^(?P<content>.*)\s\(Source:\s(?P<source>.*?)\.\sRead more:\s(?P<url>.*?)\)$",
    re.DOTALL,
)


@app.get("/news", response_model=list[schemas.NewsItemOut])
def get_news(limit: int = 12, db: Session = Depends(get_db)):
    articles = (
        db.query(models.EmbeddedContent)
        .filter(models.EmbeddedContent.source == "news")
        .order_by(models.EmbeddedContent.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for article in articles:
        match = NEWS_SOURCE_PATTERN.match(article.content)
        if match:
            content = match.group("content")
            source = match.group("source")
            url = match.group("url")
        else:
            content = article.content
            source = "Unknown source"
            url = ""

        results.append(
            schemas.NewsItemOut(
                id=article.id,
                title=article.title or "",
                content=content,
                source=source,
                url=url,
                tags=article.tags or [],
                created_at=article.created_at,
            )
        )
    return results


# ============================================================
# Challenge Mode (day-by-day blind historical simulation)
# ============================================================
def _get_challenge_trading_days(db: Session, session: models.ChallengeSession) -> list[date]:
    """
    Reconstructs the session's exact ordered trading-day list from its
    start_date/end_date (set to the first/last day of the capped slice at
    creation time) -- deterministic since price_history doesn't change, so
    no need to persist the day list itself.
    """
    rows = (
        db.query(models.PriceHistory.date)
        .filter(
            models.PriceHistory.ticker.in_(MARKET_WATCH_TICKERS),
            models.PriceHistory.date >= session.start_date,
            models.PriceHistory.date <= session.end_date,
        )
        .group_by(models.PriceHistory.date)
        .having(func.count(func.distinct(models.PriceHistory.ticker)) == len(MARKET_WATCH_TICKERS))
        .order_by(models.PriceHistory.date.asc())
        .all()
    )
    return [r[0] for r in rows]


def _get_challenge_day_prices(db: Session, day: date) -> dict[str, float]:
    rows = (
        db.query(models.PriceHistory.ticker, models.PriceHistory.close)
        .filter(models.PriceHistory.ticker.in_(MARKET_WATCH_TICKERS), models.PriceHistory.date == day)
        .all()
    )
    return {ticker: float(close) for ticker, close in rows}


def _build_challenge_prices_payload(
    prices_today: dict[str, float], prices_yesterday: dict[str, float] | None
) -> dict:
    """
    Keyed by company name (not ticker) per the Challenge Mode API contract.
    change_pct/is_up are only included once there's a previous day to
    compare against -- day 1 always omits them.
    """
    payload = {}
    for ticker in MARKET_WATCH_TICKERS:
        price = prices_today.get(ticker)
        if price is None:
            continue
        entry = {"ticker": ticker, "price": round(price, 2), "change_pct": None}
        if prices_yesterday is not None:
            prev = prices_yesterday.get(ticker)
            if prev:
                change_pct = round((price - prev) / prev * 100, 2)
                entry["change_pct"] = change_pct
                entry["is_up"] = change_pct >= 0
        payload[COMPANY_NAMES[ticker]] = entry
    return payload


def _compute_challenge_portfolio_value(
    virtual_cash: float, holdings: dict, prices_today: dict[str, float]
) -> float:
    value = virtual_cash
    for ticker, h in holdings.items():
        price = prices_today.get(ticker, h.get("avg_buy_price", 0))
        value += h["quantity"] * price
    return round(value, 2)


@app.post("/users/{user_id}/challenge/start")
def start_challenge(
    user_id: uuid.UUID,
    payload: schemas.ChallengeStartRequest,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    candidates = [s for s in CHALLENGE_SCENARIOS if s["difficulty"] == payload.difficulty]
    scenario = random.choice(candidates)

    start = date.fromisoformat(scenario["start"])
    end = date.fromisoformat(scenario["end"])
    trading_days = (
        db.query(models.PriceHistory.date)
        .filter(
            models.PriceHistory.ticker.in_(MARKET_WATCH_TICKERS),
            models.PriceHistory.date >= start,
            models.PriceHistory.date <= end,
        )
        .group_by(models.PriceHistory.date)
        .having(func.count(func.distinct(models.PriceHistory.ticker)) == len(MARKET_WATCH_TICKERS))
        .order_by(models.PriceHistory.date.asc())
        .limit(scenario["days"])
        .all()
    )
    trading_days = [r[0] for r in trading_days]
    if not trading_days:
        raise HTTPException(status_code=500, detail="No price data available for this scenario")

    session = models.ChallengeSession(
        user_id=user_id,
        scenario_id=scenario["id"],
        difficulty=scenario["difficulty"],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        current_day_index=0,
        virtual_cash=payload.starting_balance,
        starting_balance=payload.starting_balance,
        holdings={},
        trade_log=[],
        is_complete=False,
        revealed=False,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    prices_today = _get_challenge_day_prices(db, trading_days[0])

    return {
        "session_id": str(session.id),
        "day_number": 1,
        "total_days": len(trading_days),
        "difficulty": session.difficulty,
        "virtual_cash": float(session.virtual_cash),
        "starting_balance": float(session.starting_balance),
        "holdings": {},
        "portfolio_value": float(session.virtual_cash),
        "portfolio_change_pct": 0.0,
        "prices": _build_challenge_prices_payload(prices_today, None),
        "is_complete": False,
        "revealed": False,
    }


@app.get("/users/{user_id}/challenge/active")
def get_active_challenge(user_id: uuid.UUID, db: Session = Depends(get_db)):
    session = (
        db.query(models.ChallengeSession)
        .filter(
            models.ChallengeSession.user_id == user_id,
            models.ChallengeSession.is_complete.is_(False),
        )
        .order_by(models.ChallengeSession.created_at.desc())
        .first()
    )
    if not session:
        return None

    trading_days = _get_challenge_trading_days(db, session)
    idx = session.current_day_index
    prices_today = _get_challenge_day_prices(db, trading_days[idx])
    prices_yesterday = _get_challenge_day_prices(db, trading_days[idx - 1]) if idx > 0 else None

    starting_balance = float(session.starting_balance)
    portfolio_value = _compute_challenge_portfolio_value(
        float(session.virtual_cash), session.holdings, prices_today
    )
    portfolio_change_pct = (
        (portfolio_value - starting_balance) / starting_balance * 100 if starting_balance else 0.0
    )

    return {
        "session_id": str(session.id),
        "day_number": idx + 1,
        "total_days": len(trading_days),
        "difficulty": session.difficulty,
        "virtual_cash": float(session.virtual_cash),
        "starting_balance": starting_balance,
        "holdings": session.holdings,
        "portfolio_value": portfolio_value,
        "portfolio_change_pct": round(portfolio_change_pct, 2),
        "prices": _build_challenge_prices_payload(prices_today, prices_yesterday),
        "is_complete": session.is_complete,
        "revealed": session.revealed,
    }


@app.post("/users/{user_id}/challenge/{session_id}/trade")
def trade_challenge(
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    payload: schemas.ChallengeTradeRequest,
    db: Session = Depends(get_db),
):
    session = (
        db.query(models.ChallengeSession)
        .filter(models.ChallengeSession.id == session_id, models.ChallengeSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Challenge session not found")
    if session.is_complete:
        raise HTTPException(status_code=400, detail="This challenge is already complete")
    if payload.ticker not in MARKET_WATCH_TICKERS:
        raise HTTPException(status_code=400, detail="Unknown ticker")

    trading_days = _get_challenge_trading_days(db, session)
    today = trading_days[session.current_day_index]
    prices_today = _get_challenge_day_prices(db, today)
    price = prices_today.get(payload.ticker)
    if price is None:
        raise HTTPException(status_code=400, detail="No price data for this ticker today")

    holdings = dict(session.holdings)
    cash = float(session.virtual_cash)

    if payload.action == "buy":
        cost = price * payload.quantity
        if cost > cash:
            raise HTTPException(status_code=400, detail="Not enough virtual cash for this trade")
        existing = holdings.get(payload.ticker)
        if existing:
            new_qty = existing["quantity"] + payload.quantity
            new_avg = ((existing["avg_buy_price"] * existing["quantity"]) + cost) / new_qty
            holdings[payload.ticker] = {"quantity": new_qty, "avg_buy_price": new_avg}
        else:
            holdings[payload.ticker] = {"quantity": payload.quantity, "avg_buy_price": price}
        cash -= cost
    else:
        existing = holdings.get(payload.ticker)
        held_qty = existing["quantity"] if existing else 0
        if payload.quantity > held_qty:
            raise HTTPException(status_code=400, detail="Not enough holdings to sell")
        proceeds = price * payload.quantity
        remaining = held_qty - payload.quantity
        if remaining <= 0:
            holdings.pop(payload.ticker, None)
        else:
            holdings[payload.ticker] = {"quantity": remaining, "avg_buy_price": existing["avg_buy_price"]}
        cash += proceeds

    trade_log = list(session.trade_log) + [{
        "ticker": payload.ticker,
        "action": payload.action,
        "quantity": payload.quantity,
        "price": round(price, 2),
        "day_number": session.current_day_index + 1,
    }]

    session.holdings = holdings
    session.virtual_cash = cash
    session.trade_log = trade_log
    db.commit()
    db.refresh(session)

    portfolio_value = _compute_challenge_portfolio_value(cash, holdings, prices_today)

    return {
        "virtual_cash": float(session.virtual_cash),
        "holdings": session.holdings,
        "portfolio_value": portfolio_value,
    }


@app.post("/users/{user_id}/challenge/{session_id}/next-day")
def next_day_challenge(user_id: uuid.UUID, session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = (
        db.query(models.ChallengeSession)
        .filter(models.ChallengeSession.id == session_id, models.ChallengeSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Challenge session not found")
    if session.is_complete:
        raise HTTPException(status_code=400, detail="This challenge is already complete")

    trading_days = _get_challenge_trading_days(db, session)
    new_index = session.current_day_index + 1

    if new_index >= len(trading_days):
        session.is_complete = True
        shown_index = len(trading_days) - 1
    else:
        shown_index = new_index

    session.current_day_index = shown_index
    db.commit()
    db.refresh(session)

    prices_today = _get_challenge_day_prices(db, trading_days[shown_index])
    prices_yesterday = (
        _get_challenge_day_prices(db, trading_days[shown_index - 1]) if shown_index > 0 else None
    )

    holdings = session.holdings
    portfolio_value = _compute_challenge_portfolio_value(float(session.virtual_cash), holdings, prices_today)
    starting_balance = float(session.starting_balance)
    portfolio_change_pct = (
        (portfolio_value - starting_balance) / starting_balance * 100 if starting_balance else 0.0
    )

    return {
        "day_number": shown_index + 1,
        "total_days": len(trading_days),
        "virtual_cash": float(session.virtual_cash),
        "holdings": holdings,
        "portfolio_value": portfolio_value,
        "portfolio_change_pct": round(portfolio_change_pct, 2),
        "prices": _build_challenge_prices_payload(prices_today, prices_yesterday),
        "is_complete": session.is_complete,
    }


@app.post("/users/{user_id}/challenge/{session_id}/reveal")
def reveal_challenge(user_id: uuid.UUID, session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = (
        db.query(models.ChallengeSession)
        .filter(models.ChallengeSession.id == session_id, models.ChallengeSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Challenge session not found")

    session.revealed = True
    db.commit()

    trading_days = _get_challenge_trading_days(db, session)
    first_day = trading_days[0]
    final_day = trading_days[-1]
    final_prices = _get_challenge_day_prices(db, final_day)
    first_prices = _get_challenge_day_prices(db, first_day)

    holdings = session.holdings
    starting_balance = float(session.starting_balance)
    user_final_value = _compute_challenge_portfolio_value(float(session.virtual_cash), holdings, final_prices)
    user_return_pct = (
        (user_final_value - starting_balance) / starting_balance * 100 if starting_balance else 0.0
    )

    nifty_first = first_prices.get("NIFTYBEES.NS")
    nifty_last = final_prices.get("NIFTYBEES.NS")
    market_return_pct = (
        (nifty_last - nifty_first) / nifty_first * 100 if nifty_first and nifty_last else 0.0
    )
    outperformance_pct = user_return_pct - market_return_pct

    challenge_scenario = next((s for s in CHALLENGE_SCENARIOS if s["id"] == session.scenario_id), None)
    historical_context = challenge_scenario["context"] if challenge_scenario else ""

    if first_day.year == final_day.year:
        actual_period = (
            f"{first_day:%B %Y}" if first_day.month == final_day.month
            else f"{first_day:%B} - {final_day:%B %Y}"
        )
    else:
        actual_period = f"{first_day:%B %Y} - {final_day:%B %Y}"

    trade_log = session.trade_log
    total_trades = len(trade_log)

    # "panic sell" = a sell on a day the broader market (Nifty 50 ETF, our
    # market proxy) was down vs the previous trading day.
    panic_sells = 0
    nifty_down_by_day: dict[int, bool] = {}
    for t in trade_log:
        if t["action"] != "sell":
            continue
        day_idx = t["day_number"] - 1
        if day_idx <= 0 or day_idx >= len(trading_days):
            continue
        if day_idx not in nifty_down_by_day:
            today_price = _get_challenge_day_prices(db, trading_days[day_idx]).get("NIFTYBEES.NS")
            prev_price = _get_challenge_day_prices(db, trading_days[day_idx - 1]).get("NIFTYBEES.NS")
            nifty_down_by_day[day_idx] = (
                today_price is not None and prev_price is not None and today_price < prev_price
            )
        if nifty_down_by_day[day_idx]:
            panic_sells += 1

    if total_trades == 0:
        best_decision = "No trades made — you watched the market without acting"
        worst_decision = "Consider making at least a few trades next time to practice decision-making"
    else:
        scored = []
        for t in trade_log:
            final_price = final_prices.get(t["ticker"])
            if final_price is None or not t["price"]:
                continue
            pct_to_end = (final_price - t["price"]) / t["price"] * 100
            # For a sell, the price falling afterward is a GOOD outcome (you got out in time).
            score = pct_to_end if t["action"] == "buy" else -pct_to_end
            scored.append((score, t, pct_to_end))

        if not scored:
            # Trades exist but none had usable price data to score against.
            best_decision = "Not enough price data to evaluate your trades."
            worst_decision = best_decision
        else:
            scored.sort(key=lambda x: x[0])

            def describe(entry):
                score, trade, pct = entry
                verb = "Buying" if trade["action"] == "buy" else "Selling"
                direction = "rose" if pct >= 0 else "fell"
                outcome = "paid off" if score >= 0 else "cost you"
                company_name = COMPANY_NAMES.get(trade["ticker"], trade["ticker"])
                return (
                    f"{verb} {trade['quantity']} shares of {company_name} on day "
                    f"{trade['day_number']} {outcome} -- the stock {direction} "
                    f"{abs(pct):.1f}% by the end of the challenge."
                )

            best_decision = describe(scored[-1])
            if len(scored) == 1:
                # Best and worst would be the exact same trade -- don't show
                # it twice as if they were two different decisions.
                worst_decision = "With only one trade it's hard to identify a worst decision — try more trades next time"
            else:
                worst_decision = describe(scored[0])

    if outperformance_pct > 10:
        verdict = f"Outstanding! You beat the market by {outperformance_pct:.1f}% during {actual_period}."
    elif outperformance_pct > 0:
        verdict = f"You edged out the market by {outperformance_pct:.1f}% during {actual_period} -- nice work."
    elif outperformance_pct > -10:
        verdict = f"You landed close to the market, {abs(outperformance_pct):.1f}% behind, during {actual_period}."
    else:
        verdict = f"Tough round -- the market beat you by {abs(outperformance_pct):.1f}% during {actual_period}."

    return {
        "scenario_id": session.scenario_id,
        "actual_period": actual_period,
        "historical_context": historical_context,
        "difficulty": session.difficulty,
        "user_final_value": round(user_final_value, 2),
        "user_return_pct": round(user_return_pct, 2),
        "market_return_pct": round(market_return_pct, 2),
        "outperformance_pct": round(outperformance_pct, 2),
        "behavior_analysis": {
            "total_trades": total_trades,
            "panic_sells": panic_sells,
            "best_decision": best_decision,
            "worst_decision": worst_decision,
        },
        "verdict": verdict,
    }


@app.post("/users/{user_id}/challenge/{session_id}/abandon")
def abandon_challenge(user_id: uuid.UUID, session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = (
        db.query(models.ChallengeSession)
        .filter(models.ChallengeSession.id == session_id, models.ChallengeSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Challenge session not found")

    # Marked complete+revealed (not deleted) so it drops out of GET /active
    # but the record -- and its trade history -- is preserved.
    session.is_complete = True
    session.revealed = True
    db.commit()

    return {"message": "Challenge abandoned"}