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
def generate_strategy(
    risk_profile: dict,
    behavior_score: dict | None = None,
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
AVAILABLE MODULES (you MUST only use titles from this list exactly as written):
{module_list}

INSTRUCTIONS:
1. Select 4 to 6 modules from the list above appropriate for this user's risk profile.
2. Order them from foundational to advanced.
3. For each module decide type: "fixed" (guided lesson) or "sandbox" (user runs their own backtest).
4. Assign difficulty: "easy", "medium", or "hard".
5. For "fixed" modules assign xp (10-100). For "sandbox" modules set xp to null.
6. For "sandbox" modules set asset_class to "equity", "etf", or "bond". For "fixed" set asset_class to null.
7. Write a short rationale (1-2 sentences) for each module.

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