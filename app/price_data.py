"""
price_data.py

DB access layer for the Simulation Environment.
The ONLY file that touches Postgres for backtesting purposes.
Converts raw price_history rows into DailyPrice objects that
backtest_engine.run_backtest() already knows how to use.

Why this is its own file, separate from backtest_engine.py:
- backtest_engine.py stays pure/testable (no DB dependency at all).
- If you ever swap Postgres for something else, or change the schema,
  only this file needs to change — the math engine doesn't care.
"""

from datetime import date
from sqlalchemy import text

from app.backtest_engine import DailyPrice
from app.database import engine  # reuse the same connection Phase 1 already set up


def get_price_data(tickers: list[str], start_date: date, end_date: date) -> list[DailyPrice]:
    """
    Fetches OHLCV rows from price_history for the given tickers and date range,
    and converts them into DailyPrice objects.

    Only `close` is pulled, because run_backtest only marks positions to market
    using closing price — open/high/low aren't needed for this engine's math.
    """
    query = text("""
        SELECT ticker, date, close
        FROM price_history
        WHERE ticker = ANY(:tickers)
          AND date BETWEEN :start_date AND :end_date
        ORDER BY date ASC
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {"tickers": tickers, "start_date": start_date, "end_date": end_date},
        ).fetchall()

    return [
        DailyPrice(ticker=row.ticker, trade_date=row.date, close=float(row.close))
        for row in rows
    ]


if __name__ == "__main__":
    # Manual smoke test — swap in a ticker + date range you know is in your DB.
    prices = get_price_data(
        tickers=["AAPL"],
        start_date=date(2023, 1, 1),
        end_date=date(2023, 1, 10),
    )
    for p in prices:
        print(p)
    print(f"\nFetched {len(prices)} rows")
