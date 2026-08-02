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

def _calculate_hhi(final_holdings: dict, final_prices: dict) -> float:
    """
    Herfindahl-Hirschman Index -- portfolio concentration by value weight.
    HHI = sum of squared weights of each holding's value / total portfolio value
    HHI = 1.0: everything in one stock (maximum concentration risk)
    HHI < 0.35: well diversified (SEBI guideline threshold)
    Reference: Adapted from industrial economics for portfolio analysis
    """
    if not final_holdings:
        return 0.0
    total_value = sum(
        qty * final_prices.get(ticker, 0)
        for ticker, qty in final_holdings.items()
    )
    if total_value <= 0:
        return 0.0
    weights = [
        (qty * final_prices.get(ticker, 0)) / total_value
        for ticker, qty in final_holdings.items()
    ]
    return round(sum(w ** 2 for w in weights), 3)


def _calculate_disposition_effect(
    sell_trades: list[dict],
    final_holdings: dict,
    avg_buy_prices: dict,
    final_prices: dict,
) -> float:
    """
    Disposition Effect = PGR - PLR
    PGR = Proportion of Gains Realized (sold winners / all winners)
    PLR = Proportion of Losses Realized (sold losers / all losers)
    Positive = selling winners and holding losers (BAD -- classic bias)
    Negative = holding winners and cutting losers (GOOD -- disciplined)
    Reference: Shefrin & Statman (1985), Journal of Finance

    sell_trades/avg_buy_prices/final_prices are dicts (not TradeRecord
    objects) sourced from metrics["executed_trades"] via
    _derive_price_context -- see that function's docstring for why.
    """
    gains_realized = 0
    losses_realized = 0
    gains_held = 0
    losses_held = 0

    for trade in sell_trades:
        avg_cost = avg_buy_prices.get(trade["ticker"], trade["price"])
        if trade["price"] > avg_cost:
            gains_realized += 1
        else:
            losses_realized += 1

    for ticker, qty in final_holdings.items():
        if qty <= 0:
            continue
        current = final_prices.get(ticker, 0)
        avg_cost = avg_buy_prices.get(ticker, current)
        if current > avg_cost:
            gains_held += 1
        else:
            losses_held += 1

    pgr = gains_realized / max(1, gains_realized + gains_held)
    plr = losses_realized / max(1, losses_realized + losses_held)
    return round(pgr - plr, 3)


def _derive_price_context(metrics: dict) -> tuple[dict, dict, dict, list]:
    """
    HHI and disposition effect both need trade prices, which the
    caller-supplied `trades` list doesn't have (it's just ticker/action/
    quantity/trade_date -- see compute_behavior_metrics' docstring).
    Prices only exist on metrics["executed_trades"], written by the
    backtest engine's actual fills. This module has no live price lookup
    of its own, so final_prices is proxied from each ticker's most recent
    executed price (executed_trades is chronological, so simply overwriting
    per ticker while iterating lands on the latest one).

    Returns (final_holdings, avg_buy_prices, final_prices, sell_trades).
    """
    executed_trades = metrics.get("executed_trades", [])

    final_holdings: dict[str, int] = {}
    buy_cost_qty: dict[str, list[float]] = {}
    final_prices: dict[str, float] = {}

    for t in executed_trades:
        ticker = t["ticker"]
        final_prices[ticker] = t["price"]
        if t["action"] == "buy":
            final_holdings[ticker] = final_holdings.get(ticker, 0) + t["quantity"]
            cost, qty = buy_cost_qty.get(ticker, [0.0, 0])
            buy_cost_qty[ticker] = [cost + t["price"] * t["quantity"], qty + t["quantity"]]
        elif t["action"] == "sell":
            final_holdings[ticker] = max(0, final_holdings.get(ticker, 0) - t["quantity"])

    final_holdings = {t: q for t, q in final_holdings.items() if q > 0}
    avg_buy_prices = {
        ticker: cost / qty for ticker, (cost, qty) in buy_cost_qty.items() if qty > 0
    }
    sell_trades = [t for t in executed_trades if t["action"] == "sell"]

    return final_holdings, avg_buy_prices, final_prices, sell_trades


def compute_behavior_metrics(
    trades: list[dict],
    metrics: dict,
    final_prices: dict | None = None,
    avg_buy_prices: dict | None = None,
) -> dict:
    """
    Computes behavioral metrics from a simulation log's trades and metrics.

    trades: list of dicts from simulation_logs.trades
            e.g. [{"ticker": "AAPL", "action": "buy", "quantity": 10,
                   "trade_date": "2023-01-03"}, ...]

    metrics: dict from simulation_logs.metrics (has daily_values, executed_trades,
             drawdown etc.) -- HHI/disposition effect are derived from
             metrics["executed_trades"] (see _derive_price_context), since
             the caller-supplied `trades` above has no price data.

    final_prices/avg_buy_prices: optional overrides (ticker -> float) for
    callers with a better price source than the executed-trades proxy --
    e.g. live market prices for still-held positions. Falls back to prices
    derived from metrics["executed_trades"] when omitted.

    Returns a scores dict ready to store back into simulation_logs.metrics.
    """

    if not trades:
        return {
            "panic_sell_rate": 0.0,
            "trade_frequency": "low",
            "diversification_ratio": 0,
            "avg_holding_days": 0.0,
            "loss_realization_rate": 0.0,
            "hhi": 0.0,
            "hhi_interpretation": "No holdings to analyze",
            "disposition_effect": 0.0,
            "disposition_interpretation": "Balanced approach",
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

    # --- Metric 6: HHI concentration risk ---
    # --- Metric 7: Disposition effect (Shefrin & Statman, 1985) ---
    final_holdings, derived_avg_buy_prices, derived_final_prices, sell_trades_for_disposition = (
        _derive_price_context(metrics)
    )
    resolved_final_prices = final_prices if final_prices is not None else derived_final_prices
    resolved_avg_buy_prices = avg_buy_prices if avg_buy_prices is not None else derived_avg_buy_prices

    hhi = _calculate_hhi(final_holdings, resolved_final_prices)
    disposition_effect = _calculate_disposition_effect(
        sell_trades_for_disposition, final_holdings, resolved_avg_buy_prices, resolved_final_prices
    )

    # --- Compute flags ---
    # Only issues go in `flags` -- it feeds generate_feedback()'s "areas
    # needing improvement" prompt and the Groq-failure fallback text
    # ("Areas to watch: ..."), so a positive outcome (well diversified,
    # disciplined selling) doesn't belong here. Those still show up via
    # hhi_interpretation/disposition_interpretation below and get a silent
    # score bonus, the same way the diversification bonus already works.
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
    if hhi > 0.5:
        flags.append("high_concentration")
    elif hhi > 0.35:
        flags.append("moderate_concentration")
    if disposition_effect > 0.3:
        flags.append("disposition_bias")

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
    if "high_concentration" in flags:
        score -= 15
    elif "moderate_concentration" in flags:
        score -= 8
    elif hhi > 0 and len(final_holdings) > 1:
        score += 5
    if "disposition_bias" in flags:
        score -= 15
    elif disposition_effect < -0.1:
        score += 10
    # Bonus for good diversification
    if unique_tickers >= 3:
        score = min(100, score + 10)

    return {
        "panic_sell_rate": round(panic_sell_rate, 2),
        "trade_frequency": trade_frequency,
        "diversification_ratio": unique_tickers,
        "avg_holding_days": round(avg_holding_days, 1),
        "loss_realization_rate": round(loss_realization_rate, 2),
        "hhi": hhi,
        "hhi_interpretation": (
            "High concentration risk" if hhi > 0.5
            else "Moderate concentration" if hhi > 0.35
            else "Well diversified" if hhi > 0 and len(final_holdings) > 1
            else "No holdings to analyze"
        ),
        "disposition_effect": disposition_effect,
        "disposition_interpretation": (
            "Selling winners too early — disposition bias detected" if disposition_effect > 0.2
            else "Balanced approach" if disposition_effect > -0.1
            else "Disciplined — letting winners run, cutting losers"
        ),
        "flags": flags,
        # Two new bonuses (HHI, disposition) aren't individually clamped --
        # only the pre-existing diversification bonus caps at 100, and only
        # when unique_tickers >= 3 -- so clamp here too rather than assume
        # score never exceeds the documented 0-100 range.
        "overall_behavior_score": max(0, min(100, score)),
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
        "high_concentration": "your portfolio was heavily concentrated in very few stocks "
                              "(SEBI guidelines suggest no single holding should exceed "
                              "about 35% of a portfolio), which is called concentration risk",
        "moderate_concentration": "your portfolio showed moderate concentration in a small "
                                  "number of stocks, leaving you more exposed to single-stock "
                                  "risk than a well-spread portfolio",
        "disposition_bias": "you sold your winning positions too early while holding onto "
                            "losing ones, a well-documented bias called the disposition "
                            "effect (Shefrin & Statman, 1985)",
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
    final_prices: dict | None = None,
    avg_buy_prices: dict | None = None,
) -> dict:
    """
    Full Behavior Engine pipeline:
    1. Compute metrics (always)
    2. Generate LLM feedback (best-effort)

    final_prices/avg_buy_prices: optional overrides passed straight through
    to compute_behavior_metrics -- see its docstring.

    Returns complete behavior analysis ready to merge into
    simulation_logs.metrics.
    """
    scores = compute_behavior_metrics(
        trades, metrics, final_prices=final_prices, avg_buy_prices=avg_buy_prices
    )
    feedback = generate_feedback(scores, risk_category)

    return {
        "behavior": {
            **scores,
            "feedback": feedback,
        }
    }