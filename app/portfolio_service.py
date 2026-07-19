"""
Portfolio Service: rules-based risk scoring.

Deliberately NOT an LLM call. See architecture doc Part 2 -- this is a
deterministic weighted scoring model, same category of approach public
robo-advisors (Betterment, Wealthfront) use. Kept as a pure function
(no DB, no I/O) so it's independently unit-testable and so the FastAPI
layer stays a thin wrapper around it.
"""

from dataclasses import dataclass, asdict


# ---- Weight constants -------------------------------------------------
# Sum to 100. Change these in one place if you want to retune the model.
WEIGHT_TIME_HORIZON = 35
WEIGHT_RISK_TOLERANCE = 35
WEIGHT_SAVINGS_CUSHION = 15
WEIGHT_PCT_INVESTABLE = 15

CATEGORY_THRESHOLDS = [
    (30, "conservative"),
    (55, "moderate"),
    (75, "moderate-aggressive"),
    (100, "aggressive"),
]


@dataclass
class RiskProfileInput:
    income: float                  # annual, in your base currency
    savings: float                 # current savings/liquid assets
    goal: str                      # free text, stored but not scored
    time_horizon_years: float
    pct_income_investable: float   # 0-100
    risk_tolerance_input: int      # 1-5 self-reported


@dataclass
class RiskProfileOutput:
    risk_score: int
    category: str
    time_horizon_years: float
    score_breakdown: dict


def _score_time_horizon(years: float) -> float:
    """
    Longer horizon = more capacity to ride out volatility.
    Buckets rather than a smooth curve on purpose: a smooth linear
    scale implies false precision (there's no real difference between
    "9.8 years" and "9.9 years" of investing behavior). Buckets also
    make the score explainable to a user in plain language.
    """
    if years < 2:
        fraction = 0.15
    elif years < 5:
        fraction = 0.45
    elif years < 10:
        fraction = 0.75
    else:
        fraction = 1.0
    return fraction * WEIGHT_TIME_HORIZON


def _score_risk_tolerance(level: int) -> float:
    """Self-reported 1 (very conservative) to 5 (very aggressive)."""
    level = max(1, min(5, level))
    fraction = (level - 1) / 4  # 1->0.0, 5->1.0
    return fraction * WEIGHT_RISK_TOLERANCE


def _score_savings_cushion(savings: float, income: float) -> float:
    """
    Uses savings-to-income ratio as a proxy for a safety net, since we
    don't collect monthly expenses in this input set. A bigger cushion
    means the person can tolerate a market drawdown without needing to
    liquidate investments -- so it INCREASES risk capacity, not just
    "financial health."
    """
    if income <= 0:
        return 0.0
    ratio = savings / income
    if ratio < 0.25:
        fraction = 0.2       # thin cushion, less than 3 months of income saved
    elif ratio < 0.75:
        fraction = 0.5
    elif ratio < 1.5:
        fraction = 0.8
    else:
        fraction = 1.0        # well-cushioned
    return fraction * WEIGHT_SAVINGS_CUSHION


def _score_pct_investable(pct: float) -> float:
    """
    Weak/soft signal (someone can overstate willingness without
    understanding risk), hence the smallest weight. Still meaningful
    as a tiebreaker between two users with identical horizon/tolerance.
    """
    pct = max(0.0, min(100.0, pct))
    fraction = pct / 100.0
    return fraction * WEIGHT_PCT_INVESTABLE


def _categorize(score: int) -> str:
    for threshold, label in CATEGORY_THRESHOLDS:
        if score <= threshold:
            return label
    return CATEGORY_THRESHOLDS[-1][1]


def compute_risk_profile(data: RiskProfileInput) -> RiskProfileOutput:
    time_component = _score_time_horizon(data.time_horizon_years)
    tolerance_component = _score_risk_tolerance(data.risk_tolerance_input)
    savings_component = _score_savings_cushion(data.savings, data.income)
    pct_component = _score_pct_investable(data.pct_income_investable)

    raw_score = time_component + tolerance_component + savings_component + pct_component
    risk_score = round(raw_score)
    category = _categorize(risk_score)

    breakdown = {
        "time_horizon": round(time_component, 2),
        "risk_tolerance": round(tolerance_component, 2),
        "savings_cushion": round(savings_component, 2),
        "pct_investable": round(pct_component, 2),
        "weights": {
            "time_horizon": WEIGHT_TIME_HORIZON,
            "risk_tolerance": WEIGHT_RISK_TOLERANCE,
            "savings_cushion": WEIGHT_SAVINGS_CUSHION,
            "pct_investable": WEIGHT_PCT_INVESTABLE,
        },
    }

    return RiskProfileOutput(
        risk_score=risk_score,
        category=category,
        time_horizon_years=data.time_horizon_years,
        score_breakdown=breakdown,
    )
