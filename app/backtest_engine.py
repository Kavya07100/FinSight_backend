"""
backtest_engine.py

Core Simulation Environment engine for FinSight.
Pure calculation logic only — no FastAPI, no database calls here.
Takes price data + a list of trades, returns portfolio performance over time.

Why this is separate from the DB/API layer:
- Testable on its own: feed it fake data, check the math is right, no Postgres needed.
- Reusable by BOTH simulation modes. Fixed-path scripts its trades from the
  Strategy Agent's config; sandbox takes trades typed in by the user. Either way,
  by the time trades reach this function they look identical — same engine runs both.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal


@dataclass
class Trade:
    ticker: str
    action: Literal["buy", "sell"]
    quantity: int
    trade_date: date


@dataclass
class DailyPrice:
    ticker: str
    trade_date: date
    close: float


def run_backtest(
    trades: list[Trade],
    prices: list[DailyPrice],
    starting_cash: float,
) -> dict:
    """
    Simulates a multi-asset portfolio day by day, over the date range covered by `prices`.

    Returns:
        {
            "daily_values": [{"date": ..., "value": ...}, ...],
            "final_value": float,
            "total_return_pct": float,
            "max_drawdown_pct": float,
            "executed_trades": [{"ticker", "action", "quantity", "trade_date",
                                  "price", "cost"}, ...],
        }

    executed_trades records the REAL execution price/cost per trade (as
    opposed to the caller-supplied Trade list, which has neither) -- callers
    that dump a lump sum of cash upfront for many trades (e.g. a SIP) need
    this to tell "cash actually deployed so far" apart from cash still
    sitting idle waiting for a future trade date. Without it, portfolio
    value (cash + holdings) looks inflated relative to what's actually
    been invested at any past checkpoint.
    """
    # Reshape prices into {date: {ticker: close}} for fast lookup per day
    prices_by_date: dict[date, dict[str, float]] = {}
    for p in prices:
        prices_by_date.setdefault(p.trade_date, {})[p.ticker] = p.close

    available_dates = sorted(prices_by_date.keys())

    def _snap_to_trading_day(target: date) -> date | None:
        """
        Callers often pick a trade_date (e.g. "6 months ago") that lands on a
        weekend/holiday with no price row -- trades on those days would
        otherwise silently never execute. Snap to the nearest trading day:
        prefer the next one forward, within 7 days; if none exists that soon,
        fall back to the most recent trading day before it. Returns None only
        if there's no trading day available at all (empty price data).
        """
        if target in prices_by_date:
            return target
        for offset in range(1, 8):
            candidate = target + timedelta(days=offset)
            if candidate in prices_by_date:
                return candidate
        earlier = [d for d in available_dates if d < target]
        return max(earlier) if earlier else None

    # Reshape trades into {date: [Trade, ...]} so we know what to execute each day
    trades_by_date: dict[date, list[Trade]] = {}
    for t in trades:
        snapped_date = _snap_to_trading_day(t.trade_date)
        if snapped_date is None:
            continue  # no trading day available near this date at all
        trades_by_date.setdefault(snapped_date, []).append(t)

    cash = starting_cash
    holdings: dict[str, int] = {}  # ticker -> shares currently held

    daily_values = []
    executed_trades = []
    peak_value = starting_cash
    max_drawdown = 0.0

    for day in sorted(prices_by_date.keys()):
        day_prices = prices_by_date[day]

        # 1. Execute any trades scheduled for today, at today's close price
        for t in trades_by_date.get(day, []):
            if t.ticker not in day_prices:
                continue  # no price data for this ticker today — skip rather than crash
            price = day_prices[t.ticker]
            cost = price * t.quantity
            if t.action == "buy":
                cash -= cost
                holdings[t.ticker] = holdings.get(t.ticker, 0) + t.quantity
            elif t.action == "sell":
                cash += cost
                holdings[t.ticker] = holdings.get(t.ticker, 0) - t.quantity
            executed_trades.append({
                "ticker": t.ticker,
                "action": t.action,
                "quantity": t.quantity,
                "trade_date": day,  # actual execution day, post-snap -- may differ from t.trade_date
                "price": price,
                "cost": cost,
            })

        # 2. Mark-to-market: value the ENTIRE portfolio at today's close prices
        holdings_value = sum(
            shares * day_prices.get(ticker, 0)
            for ticker, shares in holdings.items()
        )
        portfolio_value = cash + holdings_value
        daily_values.append({"date": day, "value": portfolio_value})

        # 3. Track drawdown as we walk forward (needs the running peak, not just start/end)
        peak_value = max(peak_value, portfolio_value)
        drawdown = (peak_value - portfolio_value) / peak_value
        max_drawdown = max(max_drawdown, drawdown)

    final_value = daily_values[-1]["value"] if daily_values else starting_cash
    total_return_pct = (final_value - starting_cash) / starting_cash * 100

    return {
        "daily_values": daily_values,
        "final_value": final_value,
        "total_return_pct": total_return_pct,
        "max_drawdown_pct": max_drawdown * 100,
        "executed_trades": executed_trades,
    }


if __name__ == "__main__":
    # Quick manual test: $10,000 cash, buy 10 shares of AAPL on day 1,
    # sell them on day 3. Sanity-check the math by hand against this output.
    prices = [
        DailyPrice("AAPL", date(2024, 1, 1), 100.0),
        DailyPrice("AAPL", date(2024, 1, 2), 110.0),
        DailyPrice("AAPL", date(2024, 1, 3), 90.0),
    ]
    trades = [
        Trade("AAPL", "buy", 10, date(2024, 1, 1)),
        Trade("AAPL", "sell", 10, date(2024, 1, 3)),
    ]

    result = run_backtest(trades, prices, starting_cash=10000.0)
    for row in result["daily_values"]:
        print(row)
    print("Final value:", result["final_value"])
    print("Total return %:", result["total_return_pct"])
    print("Max drawdown %:", result["max_drawdown_pct"])
