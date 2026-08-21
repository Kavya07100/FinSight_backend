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
from sqlalchemy import text

from app.database import engine

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])
GENERATION_MODEL = "llama-3.3-70b-versatile"


# ------------------------------------------------------------------
# Step 1: Retrieve available content titles from embedded_content
# ------------------------------------------------------------------
def retrieve_available_modules(category: str, top_k: int = 12) -> list[dict]:
    """
    Pulls a broad set of content from embedded_content so the Strategy Agent
    knows what modules actually exist to assign.
    """
    difficulty_filter = {
        "conservative": ("easy",),
        "moderate": ("easy", "medium"),
        "moderate-aggressive": ("easy", "medium", "hard"),
        "aggressive": ("medium", "hard"),
    }.get(category, ("easy", "medium", "hard"))

    placeholders = ", ".join(f":d{i}" for i in range(len(difficulty_filter)))
    params = {f"d{i}": v for i, v in enumerate(difficulty_filter)}
    params["top_k"] = top_k

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT title, tags, difficulty
                FROM embedded_content
                WHERE difficulty IN ({placeholders})
                ORDER BY difficulty ASC, created_at ASC
                LIMIT :top_k
            """),
            params,
        ).fetchall()

    return [
        {"title": r.title, "tags": r.tags, "difficulty": r.difficulty}
        for r in rows
    ]


# ------------------------------------------------------------------
# Step 2: Build the prompt and call Groq
# ------------------------------------------------------------------
def _build_strategy_prompt(
    risk_profile: dict,
    category: str,
    module_list: str,
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
    """
    category = risk_profile.get("category", "moderate")
    available_modules = retrieve_available_modules(category)

    if not available_modules:
        return [
            {
                "step": 1,
                "module": "No content available",
                "type": "fixed",
                "difficulty": "easy",
                "xp": 10,
                "asset_class": None,
                "rationale": "No educational content found in the database.",
            }
        ]

    module_list = "\n".join(
        f"- \"{m['title']}\" (difficulty: {m['difficulty']}, tags: {', '.join(m['tags'] or [])})"
        for m in available_modules
    )

    prompt = _build_strategy_prompt(
        risk_profile, category, module_list, behavior_score, behavior_flags, score_breakdown,
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

    # Strip markdown code fences if the model adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    path = json.loads(raw)
    return path