import uuid
from datetime import datetime, date
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    full_name: str | None = None
    age: int = Field(gt=0)
    monthly_income: float = Field(ge=0)
    current_savings: float = Field(ge=0)
    dependents: int | None = None
    employment_type: str | None = None
    existing_investments: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    full_name: str | None
    age: int | None
    monthly_income: float | None
    monthly_expenses: float | None = None
    current_savings: float | None
    dependents: int | None = None
    employment_type: str | None = None
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    age: int | None = Field(default=None, gt=0)
    monthly_income: float | None = Field(default=None, ge=0)
    monthly_expenses: float | None = Field(default=None, ge=0)
    current_savings: float | None = Field(default=None, ge=0)
    dependents: int | None = Field(default=None, ge=0)
    employment_type: str | None = None
    investment_goal: str | None = None
    risk_tolerance: int | None = Field(default=None, ge=1, le=5)
    time_horizon_years: float | None = Field(default=None, gt=0)


class RiskProfileRequest(BaseModel):
    """
    Onboarding-facing shape. time_horizon_years and pct_income_investable are
    now collected directly by onboarding's Step 2/3 (financial situation +
    investment goals), so they're required here rather than defaulted.
    """
    age: int = Field(gt=0)
    monthly_income: float = Field(ge=0)
    current_savings: float = Field(ge=0)
    investment_goal: str
    risk_tolerance: int = Field(ge=1, le=5, description="1=very conservative, 5=very aggressive")
    time_horizon_years: float = Field(gt=0)
    pct_income_investable: float = Field(ge=0, le=100)


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
    benchmark_ticker: Literal["SPY", "NIFTYBEES.NS"] = Field(
        default="SPY",
        description=(
            "Index/ETF to compare against via buy-and-hold. SPY = S&P 500 "
            "(global benchmark), NIFTYBEES.NS = Nifty 50 (Indian benchmark)."
        ),
    )
    scenario_id: str = Field(
        default="live",
        description="Which scenario portfolio this trade's cash/holdings apply to.",
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
# Learning Modules (article + quiz)
# ============================================================
class QuizQuestionOut(BaseModel):
    """Quiz question as sent to the client -- correct_answer is withheld."""
    id: uuid.UUID
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str


class LearningModuleOut(BaseModel):
    module_name: str
    article_content: str
    article_summary: list[str]
    difficulty: str
    module_step: int = 1
    quiz_questions: list[QuizQuestionOut]


class QuizSubmitRequest(BaseModel):
    module_name: str
    module_step: int
    answers: dict[str, str] = Field(description="question_id (str) -> chosen option (a/b/c/d)")


class QuizResultItem(BaseModel):
    question_id: str
    question: str
    your_answer: str | None
    correct_answer: str
    is_correct: bool
    explanation: str


class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    passed: bool
    xp_awarded: int
    results: list[QuizResultItem]


class XPOut(BaseModel):
    total_xp: int
    level: int
    xp_to_next_level: int
    level_label: str


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
# Scenario Portfolios (per-scenario cash + holdings isolation)
# ============================================================
class ScenarioPortfolioOut(BaseModel):
    scenario_id: str
    virtual_cash: float
    starting_balance: float
    is_started: bool
    total_invested: float
    holdings: list[HoldingOut]
    overall_return_pct: float


# ============================================================
# Challenge Mode (day-by-day blind historical simulation)
# ============================================================
class ChallengeStartRequest(BaseModel):
    difficulty: str = Field(pattern="^(easy|medium|hard|expert)$")
    starting_balance: float = Field(ge=10000, le=10000000)


class ChallengeTradeRequest(BaseModel):
    ticker: str
    action: str = Field(pattern="^(buy|sell)$")
    quantity: int = Field(gt=0)


class SetScenarioBalanceRequest(BaseModel):
    starting_balance: float = Field(ge=10000, le=10000000)


class ScenarioResetOut(BaseModel):
    message: str
    virtual_cash: float


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