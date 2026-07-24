"""
scripts/ingest_prices.py

One-off / periodic data pipeline: pulls historical OHLCV price data from
Yahoo Finance (via yfinance) and loads it into the price_history table.

Deliberately NOT part of the FastAPI app (app/) -- this is a script you run
by hand (or later, on a schedule) to load/refresh data. Same spirit as the
architecture doc's News Agent being "a scheduled job, not a full agent" --
not everything needs to be a live API endpoint.

Why yfinance for now: free, no API key, good enough to get real data into
a capstone demo today. When you move to a paid provider later, this is the
ONLY file that needs to change -- price_history's shape stays the same, so
backtest_engine.py and price_data.py don't care where the rows came from.
"""

import math
import yfinance as yf
from datetime import date as date_cls
from sqlalchemy import text

from app.database import engine

# Starter set: individual stocks (for single-stock lessons) + broad ETFs
# (for diversification lessons). Add more tickers here any time -- nothing
# else in the codebase needs to change when you do.
TICKERS = [
    "RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TMPV.NS",
    "WIPRO.NS", "BAJFINANCE.NS", "NIFTYBEES.NS", "SBIN.NS", "SPY"
]

START_DATE = "2022-01-01"
# Computed at run time, not hardcoded -- the frontend's simulate page always
# requests "1 year ago through today," so a fixed END_DATE silently goes
# stale and every simulation 400s once "today" moves past it.
END_DATE = date_cls.today().isoformat()


def ingest():
    with engine.connect() as conn:
        for ticker in TICKERS:
            print(f"Fetching {ticker}...")
            df = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)

            if df.empty:
                print(f"  No data returned for {ticker}, skipping.")
                continue

            rows_done = 0
            rows_skipped = 0
            for date, row in df.iterrows():
                open_ = float(row["Open"].iloc[0]) if hasattr(row["Open"], "iloc") else float(row["Open"])
                high = float(row["High"].iloc[0]) if hasattr(row["High"], "iloc") else float(row["High"])
                low = float(row["Low"].iloc[0]) if hasattr(row["Low"], "iloc") else float(row["Low"])
                close = float(row["Close"].iloc[0]) if hasattr(row["Close"], "iloc") else float(row["Close"])
                volume = int(row["Volume"].iloc[0]) if hasattr(row["Volume"], "iloc") else int(row["Volume"])

                if any(math.isnan(v) for v in (open_, high, low, close)):
                    # yfinance occasionally returns an incomplete bar --
                    # most often for the most recent trading day while it's
                    # still mid-session -- with NaN OHLC values. Postgres's
                    # NUMERIC type will happily store 'NaN', but it then
                    # poisons any backtest whose trades touch that date:
                    # NaN + anything = NaN, and it never recovers for the
                    # rest of that run.
                    rows_skipped += 1
                    continue

                # ON CONFLICT here uses the UNIQUE(ticker, date) constraint
                # already in schema.sql -- re-running this script just
                # updates existing rows instead of erroring or duplicating.
                conn.execute(
                    text("""
                        INSERT INTO price_history (ticker, date, open, high, low, close, volume)
                        VALUES (:ticker, :date, :open, :high, :low, :close, :volume)
                        ON CONFLICT (ticker, date) DO UPDATE SET
                            open = EXCLUDED.open,
                            high = EXCLUDED.high,
                            low = EXCLUDED.low,
                            close = EXCLUDED.close,
                            volume = EXCLUDED.volume
                    """),
                    {
                        "ticker": ticker,
                        "date": date.date(),
                        "open": open_,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": volume,
                    },
                )
                rows_done += 1

            conn.commit()
            skip_note = f" ({rows_skipped} skipped for NaN OHLC)" if rows_skipped else ""
            print(f"  Inserted/updated {rows_done} rows for {ticker}{skip_note}")

    print("Done.")


if __name__ == "__main__":
    ingest()
