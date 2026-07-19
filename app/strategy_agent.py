"""
app/strategy_agent.py

Strategy Agent: given a user's risk profile (and, on later runs, behavior
feedback), produces a structured JSON learning path that the Simulation
Environment can consume.

This is an LLM reasoning task -- not rules-based -- because the sequencing
and difficulty curve require judgment about which concepts should precede
which, given a specific risk picture.

Two phases every time it runs:
  1. Retrieve available content from embedded_content (so the LLM builds
     a path from modules that actually exist, not invented names).
  2. Call Gemini with a schema-constrained prompt so the output is always
     valid JSON -- no parsing failures.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from sqlalchemy import text

from app.database import engine

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
GENERATION_MODEL = "gemini-1.5-flash"


# ------------------------------------------------------------------
# Step 1: Retrieve available content titles from embedded_content
# ------------------------------------------------------------------
def retrieve_available_modules(category: str, top_k: int = 12) -> list[dict]:
    """
    Pulls a broad set of content from embedded_content so the Strategy Agent
    knows what modules actually exist.

    Unlike Learning Agent retrieval (which finds the closest match to a
    specific question), this retrieval is intentionally broad: we want a
    diverse menu of options, not just the top-3 nearest neighbors to one query.

    Strategy: pull the highest-difficulty content for aggressive profiles,
    lowest for conservative, and a mix for moderate. This is a heuristic
    pre-filter -- the LLM still decides the final order and selection.
    """
    # Map risk category to difficulty filter so the module menu is relevant
    difficulty_filter = {
        "conservative": ("easy", "medium"),
        "moderate": ("easy", "medium", "hard"),
        "moderate-aggressive": ("medium", "hard"),
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
# Step 2: Build the prompt and call Gemini
# ------------------------------------------------------------------
def generate_strategy(
    risk_profile: dict,
    behavior_score: dict | None = None,
) -> list[dict]:
    """
    Core Strategy Agent call.

    risk_profile: dict with keys matching RiskProfile columns
                  (risk_score, category, time_horizon_years, goal,
                   score_breakdown, etc.)
    behavior_score: None on first run; populated by Behavior Engine on
                    subsequent runs. Shape TBD -- for now, if passed,
                    it's included in the prompt as context.

    Returns: list of module dicts (the "path"), ready to store in
             strategy_configs.path as JSONB.
    """
    category = risk_profile.get("category", "moderate")
    available_modules = retrieve_available_modules(category)

    if not available_modules:
        # Fallback: no content in DB yet. Return a minimal placeholder path
        # rather than crashing -- the agent can't do its job without content.
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

    # Format the module menu for the prompt
    module_list = "\n".join(
        f"- \"{m['title']}\" (difficulty: {m['difficulty']}, tags: {', '.join(m['tags'] or [])})"
        for m in available_modules
    )

    # Format behavior context if present (will be empty on first run)
    behavior_context = ""
    if behavior_score:
        behavior_context = f"""
The user has previously completed simulations. Here is their behavior analysis:
{behavior_score}

Use this to adjust the path -- for example, if they panic-sold on drawdowns,
include risk management content earlier. If they over-traded, include content
on patience and long-term thinking.
"""

    prompt = f"""You are a financial literacy curriculum designer for a retail investing education platform.
Your job is to create a personalized learning path for a user based on their risk profile.

USER RISK PROFILE:
- Risk score: {risk_profile.get('risk_score')} / 100
- Category: {category}
- Investment goal: {risk_profile.get('goal')}
- Time horizon: {risk_profile.get('time_horizon_years')} years
- % of income they can invest: {risk_profile.get('pct_income_investable')}%
- Self-reported risk tolerance (1=very conservative, 5=very aggressive): {risk_profile.get('risk_tolerance_input')}
{behavior_context}
AVAILABLE MODULES (you MUST only use titles from this list — do not invent new ones):
{module_list}

INSTRUCTIONS:
1. Select 4 to 6 modules from the list above that are appropriate for this user's risk profile.
2. Order them from foundational to advanced — earlier steps should build the knowledge needed for later ones.
3. For each module, decide whether it should be type "fixed" (guided lesson with XP reward) or "sandbox" (user runs their own backtest simulation). Foundational/conceptual modules are usually "fixed"; application/practice modules are usually "sandbox".
4. Assign a difficulty: "easy", "medium", or "hard". Match the user's risk category — conservative users should start easier; aggressive users can handle more medium/hard content.
5. For "fixed" modules, assign an xp value (10–100, higher for harder content).
6. For "sandbox" modules, set asset_class to the most relevant asset class ("equity", "etf", "bond") based on the module's tags. Leave xp as null.
7. Write a short rationale (1–2 sentences) explaining why each module was selected for this specific user.

Respond ONLY with the JSON array. No explanation, no markdown, no preamble.
"""

    # Schema-constrained generation: Gemini will enforce this structure,
    # so the response is guaranteed to be valid JSON in this shape.
    response_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "step":        {"type": "integer"},
                "module":      {"type": "string"},
                "type":        {"type": "string", "enum": ["fixed", "sandbox"]},
                "difficulty":  {"type": "string", "enum": ["easy", "medium", "hard"]},
                "xp":          {"type": "integer", "nullable": True},
                "asset_class": {"type": "string",  "nullable": True},
                "rationale":   {"type": "string"},
            },
            "required": ["step", "module", "type", "difficulty", "rationale"],
        },
    }

    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
        ),
    )

    import json
    path = json.loads(response.text)
    return path