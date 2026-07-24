import uuid
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    full_name: str | None = None
    age: int = Field(gt=0)
    monthly_income: float = Field(ge=0)
    current_savings: float = Field(ge=0)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str | None
    age: int | None
    monthly_income: float | None
    current_savings: float | None
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    age: int | None = Field(default=None, gt=0)
    monthly_income: float | None = Field(default=None, ge=0)
    current_savings: float | None = Field(default=None, ge=0)
    investment_goal: str | None = None
    risk_tolerance: int | None = Field(default=None, ge=1, le=5)


class RiskProfileRequest(BaseModel):
    """
    Onboarding-facing shape. time_horizon_years and pct_income_investable
    aren't collected by onboarding yet, so compute_and_store_risk_profile()
    fills them with DEFAULT_TIME_HORIZON_YEARS / DEFAULT_PCT_INCOME_INVESTABLE
    (see main.py) before calling the Portfolio Service.
    """
    age: int = Field(gt=0)
    monthly_income: float = Field(ge=0)
    current_savings: float = Field(ge=0)
    investment_goal: str
    risk_tolerance: int = Field(ge=1, le=5, description="1=very conservative, 5=very aggressive")


class RiskProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    version: int
    risk_score: int
    category: str
    goal: str
    risk_tolerance_input: int
    time_horizon_years: float
    score_breakdown: dict
    computed_at: datetime


# ============================================================
# Simulation Environment (sandbox mode)
# ============================================================
class TradeIn(BaseModel):
    """One trade instruction coming in from the frontend."""
    ticker: str
    action: str = Field(pattern="^(buy|sell)$")
    quantity: int = Field(gt=0)
    trade_date: date


class SandboxSimulationRequest(BaseModel):
    """
    What the frontend sends when a user runs a sandbox backtest.
    tickers is separate from trades.ticker on purpose: it defines which
    price history to load, even for tickers the user hasn't traded yet
    at request time -- keeps price-loading and trading decoupled.
    """
    tickers: list[str] = Field(min_length=1)
    start_date: date
    end_date: date
    starting_cash: float = Field(gt=0)
    trades: list[TradeIn]
    benchmark_ticker: str = Field(
        default="SPY",
        description="Index/ETF to compare against via buy-and-hold. Defaults to SPY (S&P 500).",
    )


class SimulationResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    mode: str
    trades: list[dict]
    metrics: dict
    started_at: datetime
    ended_at: datetime | None


# ============================================================
# Learning Agent (RAG)
# ============================================================
class LearningAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class LearningAskResponse(BaseModel):
    answer: str
    sources: list[str]

# ============================================================
# Strategy Agent
# ============================================================
class StrategyModuleOut(BaseModel):
    """One step in the learning path."""
    step: int
    module: str
    type: str          # "fixed" or "sandbox"
    difficulty: str    # "easy", "medium", "hard"
    xp: int | None = None           # fixed modules only
    asset_class: str | None = None  # sandbox modules only
    rationale: str


class StrategyConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    version: int
    risk_profile_id: uuid.UUID
    path: list[dict]   # stored as JSONB; frontend gets raw list of module dicts
    created_at: datetime

    # ============================================================
# Strategy Agent
# ============================================================
class StrategyModuleOut(BaseModel):
    """One step in the learning path."""
    step: int
    module: str
    type: str
    difficulty: str
    xp: int | None = None
    asset_class: str | None = None
    rationale: str


class StrategyConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    version: int
    risk_profile_id: uuid.UUID
    path: list[dict]
    created_at: datetime

    # ============================================================
# Portfolio Engine
# ============================================================
class HoldingOut(BaseModel):
    """
    Built from a PortfolioHolding row plus live price_history lookups --
    current_price/current_value/pnl_pct aren't stored, they're computed
    per-request in GET /users/{user_id}/portfolio.
    """
    id: uuid.UUID
    ticker: str
    company_name: str | None
    quantity: int
    avg_buy_price: float
    current_price: float
    current_value: float
    pnl_pct: float


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ticker: str
    company_name: str | None
    action: str
    quantity: int
    price: float
    total_value: float
    trade_date: date
    created_at: datetime


class PortfolioOut(BaseModel):
    holdings: list[HoldingOut]
    total_value: float
    total_invested: float
    overall_return_pct: float
    today_pnl: float


# ============================================================
# News
# ============================================================
class NewsItemOut(BaseModel):
    """
    embedded_content stores the real publication name and article URL
    embedded inside `content` text (not in dedicated columns) -- GET /news
    parses them back out. `content` here is the cleaned article text with
    that "(Source: ... Read more: ...)" suffix stripped off; the frontend
    truncates it for the card view and shows the full text on "Read more".
    """
    id: uuid.UUID
    title: str
    content: str
    source: str
    url: str
    tags: list[str]
    created_at: datetime


class NewsRefreshOut(BaseModel):
    inserted: int
    skipped: int
    errors: int


# ============================================================
# Behavior Engine
# ============================================================
class BehaviorAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    mode: str
    trades: list[dict]
    metrics: dict
    started_at: datetime
    ended_at: datetime | None