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

import yfinance as yf
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
END_DATE = "2024-12-31"


def ingest():
    with engine.connect() as conn:
        for ticker in TICKERS:
            print(f"Fetching {ticker}...")
            df = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False)

            if df.empty:
                print(f"  No data returned for {ticker}, skipping.")
                continue

            rows_done = 0
            for date, row in df.iterrows():
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
                        "open": float(row["Open"].iloc[0]) if hasattr(row["Open"], "iloc") else float(row["Open"]),
                        "high": float(row["High"].iloc[0]) if hasattr(row["High"], "iloc") else float(row["High"]),
                        "low": float(row["Low"].iloc[0]) if hasattr(row["Low"], "iloc") else float(row["Low"]),
                        "close": float(row["Close"].iloc[0]) if hasattr(row["Close"], "iloc") else float(row["Close"]),
                        "volume": int(row["Volume"].iloc[0]) if hasattr(row["Volume"], "iloc") else int(row["Volume"]),
                    },
                )
                rows_done += 1

            conn.commit()
            print(f"  Inserted/updated {rows_done} rows for {ticker}")

    print("Done.")


if __name__ == "__main__":
    ingest()
