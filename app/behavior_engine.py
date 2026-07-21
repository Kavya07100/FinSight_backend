"""
app/behavior_engine.py

Behavior Engine: analyzes a completed simulation session and produces
behavioral metrics + human-readable feedback.

Two layers:
  1. Analytics (pure Python math) -- computes metrics from trades + prices
  2. LLM feedback (Groq) -- turns metrics into plain-English explanation

Layer 1 always runs. Layer 2 is best-effort -- if Groq fails, the metrics
are still returned without feedback text.
"""

import os
import json
from datetime import date, timedelta
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ["GROQ_API_KEY"])
GENERATION_MODEL = "llama-3.3-70b-versatile"


# ------------------------------------------------------------------
# Layer 1: Analytics
# ------------------------------------------------------------------

def compute_behavior_metrics(trades: list[dict], metrics: dict) -> dict:
    """
    Computes behavioral metrics from a simulation log's trades and metrics.

    trades: list of dicts from simulation_logs.trades
            e.g. [{"ticker": "AAPL", "action": "buy", "quantity": 10,
                   "trade_date": "2023-01-03"}, ...]

    metrics: dict from simulation_logs.metrics (has daily_values, drawdown etc.)

    Returns a scores dict ready to store back into simulation_logs.metrics.
    """

    if not trades:
        return {
            "panic_sell_rate": 0.0,
            "trade_frequency": "low",
            "diversification_ratio": 0,
            "avg_holding_days": 0.0,
            "loss_realization_rate": 0.0,
            "flags": [],
            "overall_behavior_score": 50,
        }

    # --- Parse trade dates ---
    for t in trades:
        if isinstance(t["trade_date"], str):
            t["trade_date"] = date.fromisoformat(t["trade_date"])

    buys = [t for t in trades if t["action"] == "buy"]
    sells = [t for t in trades if t["action"] == "sell"]

    # --- Metric 1: Diversification ratio ---
    # How many distinct tickers did they trade?
    unique_tickers = len(set(t["ticker"] for t in trades))

    # --- Metric 2: Trade frequency ---
    # Trades per week relative to simulation length
    all_dates = [t["trade_date"] for t in trades]
    if len(all_dates) > 1:
        sim_days = (max(all_dates) - min(all_dates)).days or 1
        trades_per_week = len(trades) / (sim_days / 7)
    else:
        trades_per_week = len(trades)

    if trades_per_week > 3:
        trade_frequency = "high"
    elif trades_per_week > 1:
        trade_frequency = "medium"
    else:
        trade_frequency = "low"

    # --- Metric 3: Average holding period ---
    # For each sell, find the most recent buy of the same ticker
    holding_days = []
    for sell in sells:
        matching_buys = [
            b for b in buys
            if b["ticker"] == sell["ticker"]
            and b["trade_date"] <= sell["trade_date"]
        ]
        if matching_buys:
            last_buy = max(matching_buys, key=lambda b: b["trade_date"])
            days_held = (sell["trade_date"] - last_buy["trade_date"]).days
            holding_days.append(days_held)

    avg_holding_days = sum(holding_days) / len(holding_days) if holding_days else 0.0

    # --- Metric 4: Panic sell rate ---
    # Did the user sell within 3 days of a portfolio local low?
    # We detect local lows from daily_values in metrics.
    daily_values = metrics.get("daily_values", [])
    panic_sells = 0

    if daily_values and sells:
        # Parse daily value dates
        dv = [
            {"date": date.fromisoformat(d["date"]), "value": d["value"]}
            for d in daily_values
        ]

        for sell in sells:
            sell_date = sell["trade_date"]
            # Look at the 5 days before this sell
            window = [
                d for d in dv
                if sell_date - timedelta(days=5) <= d["date"] <= sell_date
            ]
            if len(window) >= 2:
                # Check if portfolio was declining into the sell
                values_in_window = [d["value"] for d in window]
                if values_in_window[-1] < values_in_window[0]:
                    # Portfolio was falling when they sold -- likely panic
                    panic_sells += 1

    panic_sell_rate = panic_sells / len(sells) if sells else 0.0

    # --- Metric 5: Loss realization rate ---
    # What % of sells were at a loss vs the starting portfolio value?
    # Simple proxy: if total_return is negative AND they sold, they realized losses
    total_return = metrics.get("total_return_pct", 0)
    loss_realization_rate = 0.0
    if sells and total_return < 0:
        # Rough proxy: proportion of sells that happened during negative return
        loss_realization_rate = min(abs(total_return) / 100, 1.0)

    # --- Compute flags ---
    flags = []
    if panic_sell_rate > 0.4:
        flags.append("panic_selling")
    if trade_frequency == "high":
        flags.append("over_trading")
    if unique_tickers < 2:
        flags.append("under_diversified")
    if avg_holding_days < 3 and sells:
        flags.append("short_term_thinking")
    if loss_realization_rate > 0.3:
        flags.append("loss_realization")

    # --- Overall behavior score (0-100, higher = healthier behavior) ---
    score = 100
    if "panic_selling" in flags:
        score -= 25
    if "over_trading" in flags:
        score -= 20
    if "under_diversified" in flags:
        score -= 20
    if "short_term_thinking" in flags:
        score -= 15
    if "loss_realization" in flags:
        score -= 10
    # Bonus for good diversification
    if unique_tickers >= 3:
        score = min(100, score + 10)

    return {
        "panic_sell_rate": round(panic_sell_rate, 2),
        "trade_frequency": trade_frequency,
        "diversification_ratio": unique_tickers,
        "avg_holding_days": round(avg_holding_days, 1),
        "loss_realization_rate": round(loss_realization_rate, 2),
        "flags": flags,
        "overall_behavior_score": max(0, score),
    }


# ------------------------------------------------------------------
# Layer 2: LLM Feedback
# ------------------------------------------------------------------

def generate_feedback(behavior_scores: dict, risk_category: str) -> str:
    """
    Takes the computed behavior metrics and generates a short, plain-English
    feedback paragraph for the user. Uses Groq/Llama.

    Returns feedback string, or a fallback string if Groq fails.
    """

    flags = behavior_scores.get("flags", [])
    overall = behavior_scores.get("overall_behavior_score", 50)

    # If no flags at all, give positive feedback without LLM
    if not flags:
        return (
            f"Great session! Your overall behavior score is {overall}/100. "
            "You showed patience, good diversification, and avoided panic selling. "
            "These are exactly the habits that lead to long-term investing success."
        )

    flag_descriptions = {
        "panic_selling": "you sold investments while the portfolio was falling, "
                         "which is a pattern called panic selling or loss aversion",
        "over_trading": "you made trades very frequently, which can increase "
                        "costs and reduce long-term returns",
        "under_diversified": "you concentrated your trades in very few tickers, "
                             "increasing your exposure to single-stock risk",
        "short_term_thinking": "your average holding period was very short, "
                               "which suggests a speculative rather than investing mindset",
        "loss_realization": "a significant portion of your sells locked in losses, "
                            "converting temporary paper losses into permanent ones",
    }

    observed = [flag_descriptions[f] for f in flags if f in flag_descriptions]
    observed_text = "; ".join(observed)

    prompt = f"""You are a financial literacy coach giving feedback to a beginner investor 
after they completed a practice simulation.

Their risk profile: {risk_category}
Their behavior score: {overall}/100
Patterns observed: {observed_text}

Write 2-3 sentences of warm, encouraging, constructive feedback. 
- Name the specific behavior pattern using its real term (e.g. "loss aversion", "over-trading")
- Explain briefly why it matters for long-term investing
- End with one actionable tip
- Keep it beginner-friendly, not condescending
- Do not use bullet points, just plain prose"""

    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly financial literacy coach. Give concise, encouraging feedback.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # Fallback if Groq fails -- still return something useful
        return (
            f"Your behavior score is {overall}/100. "
            f"Areas to watch: {', '.join(flags)}. "
            "Try to hold positions longer and diversify across more tickers."
        )


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def analyze_simulation(
    trades: list[dict],
    metrics: dict,
    risk_category: str,
) -> dict:
    """
    Full Behavior Engine pipeline:
    1. Compute metrics (always)
    2. Generate LLM feedback (best-effort)

    Returns complete behavior analysis ready to merge into
    simulation_logs.metrics.
    """
    scores = compute_behavior_metrics(trades, metrics)
    feedback = generate_feedback(scores, risk_category)

    return {
        "behavior": {
            **scores,
            "feedback": feedback,
        }
    }