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