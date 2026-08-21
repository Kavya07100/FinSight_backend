"""
app/strategy_agent.py

Strategy Agent: given a user's risk profile (and, on later runs, behavior
feedback), produces a structured JSON learning path that the Simulation
Environment can consume.

Uses Groq (Llama 3) for generation -- free tier, generous limits.
Gemini is still used for embeddings in the Learning Agent, but generation
here switches to Groq to avoid Gemini's restrictive free quota.
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])
# llama-3.3-70b-versatile was retired from Groq's catalog (calls started
# 404ing with model_not_found) -- gpt-oss-120b is the current strongest
# general-purpose model on this account, see `client.models.list()`.
GENERATION_MODEL = "openai/gpt-oss-120b"


# ------------------------------------------------------------------
# Build the prompt and call Groq
#
# The module list used to be pulled dynamically from embedded_content, but
# the prompt now hardcodes the fixed 8-module list (see IMPORTANT section
# below) so every generated path uses module names that actually exist in
# learning_modules/quiz_questions. That DB round-trip is gone with it --
# one less thing that could fail before Groq is even called.
# ------------------------------------------------------------------
def _build_strategy_prompt(
    risk_profile: dict,
    category: str,
    behavior_score: float | None,
    behavior_flags: list | None,
    score_breakdown: dict | None,
    existing_investments: bool | None = None,
) -> str:
    behavior_flags = behavior_flags or []
    score_breakdown = score_breakdown or {}
    # Weights vary if the scoring model is retuned (see portfolio_service.py's
    # WEIGHT_* constants) -- read them from the breakdown itself rather than
    # hardcoding max-points labels that would silently go stale.
    weights = score_breakdown.get("weights", {})

    score_breakdown_section = ""
    if score_breakdown:
        score_breakdown_section = f"""
Component score breakdown (out of max points):
- Time horizon score: {score_breakdown.get('time_horizon', 'N/A')} / {weights.get('time_horizon', 'N/A')}
- Risk tolerance score: {score_breakdown.get('risk_tolerance', 'N/A')} / {weights.get('risk_tolerance', 'N/A')}
- Savings cushion score: {score_breakdown.get('savings_cushion', 'N/A')} / {weights.get('savings_cushion', 'N/A')}
- Investable income score: {score_breakdown.get('pct_investable', 'N/A')} / {weights.get('pct_investable', 'N/A')}

Specific personalization flags from scores:
{f"- LOW SAVINGS CUSHION: Add 'Emergency Fund Building' as module 1" if score_breakdown.get('savings_cushion', 10) < 5 else ""}
{f"- SHORT TIME HORIZON: Prioritize liquid investments and capital preservation" if score_breakdown.get('time_horizon', 20) < 15 else ""}
{f"- LOW INVESTABLE INCOME: Add 'SIP and Rupee Cost Averaging' early in path" if score_breakdown.get('pct_investable', 5) < 3 else ""}
"""

    behavior_context = ""
    if behavior_score is not None or behavior_flags:
        behavior_context = f"""
The user has previously completed simulations. Their overall behavior score
was {behavior_score if behavior_score is not None else 'N/A'}/100.

Use this to adjust the path -- for example, if they panic-sold on drawdowns,
include risk management content earlier. If they over-traded, include content
on patience and long-term thinking.
"""

    behavior_flags_section = ""
    if behavior_flags:
        behavior_flags_section = f"""
Behavioral flags detected from trading history:
{chr(10).join(f"- {flag.upper()}: address this in learning path" for flag in behavior_flags)}

Specific module requirements based on behavioral flags:
{f"- PANIC_SELLING detected: Include 'Understanding Market Volatility' module" if 'panic_selling' in behavior_flags else ""}
{f"- DISPOSITION_BIAS detected: Include 'When to Sell: Cutting Losses Early' module" if 'disposition_bias' in behavior_flags else ""}
{f"- HIGH_CONCENTRATION detected: Include 'What is Diversification?' as priority module" if 'high_concentration' in behavior_flags else ""}
{f"- OVER_TRADING detected: Include 'SIP and Rupee Cost Averaging' and 'Risk vs Return' modules" if 'over_trading' in behavior_flags else ""}
"""

    return f"""You are a financial literacy curriculum designer for a retail investing education platform.
Your job is to create a personalized learning path for a user based on their risk profile.

USER RISK PROFILE:
- Risk score: {risk_profile.get('risk_score')} / 100
- Category: {category}
- Investment goal: {risk_profile.get('goal')}
- Time horizon: {risk_profile.get('time_horizon_years')} years
- % of income they can invest: {risk_profile.get('pct_income_investable')}%
- Self-reported risk tolerance (1=very conservative, 5=very aggressive): {risk_profile.get('risk_tolerance_input')}
{score_breakdown_section}{behavior_context}{behavior_flags_section}
{f"User already has existing investments (FD, PPF, stocks, property). Their FinSight virtual portfolio can focus on growth since they have a conservative base elsewhere." if existing_investments else "User has no existing investments — include foundational safety-first modules."}

IMPORTANT: You MUST select modules ONLY from this exact list.
Use the exact names as written — no variations, no paraphrasing:

1. Emergency Fund Building
2. SIP and Rupee Cost Averaging
3. What is a Mutual Fund?
4. What is Diversification?
5. Risk vs Return
6. Index Funds
7. Understanding Market Volatility
8. When to Sell: Cutting Losses Early

Select exactly 6 modules from this list appropriate for the user.
The module field in your JSON response must be one of these exact strings.

INSTRUCTIONS:
1. Select exactly 6 modules from the list above appropriate for this user's risk profile.
2. Order them from foundational to advanced.
3. For each module decide type: "fixed" (guided lesson) or "sandbox" (user runs their own backtest).
4. Assign difficulty: "easy", "medium", or "hard".
5. For "fixed" modules assign xp (10-100). For "sandbox" modules set xp to null.
6. For "sandbox" modules set asset_class to "equity", "etf", or "bond". For "fixed" set asset_class to null.
7. Write a short rationale (1-2 sentences) for each module.
8. If any personalization or behavioral flags above call for a specific module, prioritize including it.

Respond with ONLY a JSON array, no explanation, no markdown, no backticks. Example format:
[
  {{
    "step": 1,
    "module": "exact title from list",
    "type": "fixed",
    "difficulty": "easy",
    "xp": 50,
    "asset_class": null,
    "rationale": "reason here"
  }}
]"""


# If Groq is unreachable, times out, or returns something we can't parse
# into a usable module list, fall back to this fixed 6-module path rather
# than surfacing a 500 to the frontend (see generate_strategy below).
FALLBACK_MODULES = [
    {
        "step": 1, "module": "Emergency Fund Building",
        "type": "fixed", "difficulty": "easy", "xp": 100, "asset_class": None,
        "rationale": "Build your financial foundation first.",
    },
    {
        "step": 2, "module": "SIP and Rupee Cost Averaging",
        "type": "fixed", "difficulty": "easy", "xp": 100, "asset_class": None,
        "rationale": "Learn India's most recommended investment strategy.",
    },
    {
        "step": 3, "module": "What is a Mutual Fund?",
        "type": "fixed", "difficulty": "easy", "xp": 100, "asset_class": None,
        "rationale": "Understand the most popular Indian investment vehicle.",
    },
    {
        "step": 4, "module": "What is Diversification?",
        "type": "fixed", "difficulty": "easy", "xp": 100, "asset_class": None,
        "rationale": "Learn to spread risk across investments.",
    },
    {
        "step": 5, "module": "Risk vs Return",
        "type": "fixed", "difficulty": "medium", "xp": 100, "asset_class": None,
        "rationale": "Understand the fundamental trade-off in investing.",
    },
    {
        "step": 6, "module": "Index Funds",
        "type": "fixed", "difficulty": "medium", "xp": 100, "asset_class": None,
        "rationale": "Discover passive investing for steady long-term growth.",
    },
]


def _extract_module_list(parsed):
    """
    Groq is asked for a bare JSON array but sometimes wraps it in an object
    instead (e.g. {"modules": [...]}) despite the prompt's instructions.
    Unwrap those common shapes; raise if nothing usable is found.
    """
    if isinstance(parsed, list):
        return parsed

    if isinstance(parsed, dict):
        for key in ("modules", "path", "learning_path", "steps"):
            value = parsed.get(key)
            if isinstance(value, list):
                return value

    raise ValueError(f"Groq response was not a JSON array or a dict wrapping one (got {type(parsed).__name__})")


def generate_strategy(
    risk_profile: dict,
    behavior_score: float | None = None,
    behavior_flags: list | None = None,
    score_breakdown: dict | None = None,
    existing_investments: bool | None = None,
) -> list[dict]:
    """
    Core Strategy Agent call using Groq/Llama.
    Returns list of module dicts (the path) ready to store as JSONB.

    Any failure -- Groq being unreachable, an unexpected response shape, or
    invalid JSON -- falls back to FALLBACK_MODULES instead of raising, so a
    Groq hiccup never turns into a 500 on POST /users/{user_id}/strategy.
    """
    category = risk_profile.get("category", "moderate")

    try:
        prompt = _build_strategy_prompt(
            risk_profile, category, behavior_score, behavior_flags, score_breakdown,
            existing_investments,
        )

        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial education curriculum designer. You always respond with valid JSON arrays only, no other text.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        raw = response.choices[0].message.content.strip()
        # Best-effort logging only -- some terminals (Windows cp1252) can't
        # encode characters Groq sometimes includes (curly quotes, en-dashes),
        # and a print() crash here must never take down a response that
        # otherwise parsed fine.
        try:
            print(f"[strategy_agent] Raw Groq response:\n{raw}")
        except UnicodeEncodeError:
            print(f"[strategy_agent] Raw Groq response (non-ASCII replaced):\n{raw.encode('ascii', 'replace').decode('ascii')}")

        # Strip markdown code fences if the model adds them despite instructions
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        parsed = json.loads(raw)
        path = _extract_module_list(parsed)

        if not path:
            raise ValueError("Groq returned an empty module list")

        return path
    except Exception as exc:
        print(f"[strategy_agent] Falling back to default learning path -- {type(exc).__name__}: {exc}")
        return FALLBACK_MODULES