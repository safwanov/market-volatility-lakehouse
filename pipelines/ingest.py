"""Bronze layer: raw OHLCV from Yahoo Finance -> append-only Parquet, partitioned by ticker."""

import datetime as dt

import pandas as pd
import yfinance as yf

from pipelines.config import BRONZE, TICKERS


def ingest(start: str = "2018-01-01") -> None:
    today = dt.date.today()
    run_date = today.isoformat()
    # yfinance's `end` date is exclusive: pass tomorrow so that today's finished daily bar is included
    end = (today + dt.timedelta(days=1)).isoformat()
    for t in TICKERS:
        df = yf.download(t, start=start, end=end, auto_adjust=False, progress=False)
        if df is None or df.empty:
            raise RuntimeError(f"No data returned for {t} (rate limited or wrong ticker?)")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index().rename(columns=lambda c: str(c).lower().replace(" ", "_"))
        df["ticker"] = t
        df["ingested_at"] = pd.Timestamp.now(tz="UTC")
        out = BRONZE / f"ticker={t}"
        out.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out / f"{run_date}.parquet", index=False)  # one file per run date = idempotent re-runs
        print(f"[bronze] {t}: {len(df)} rows")


if __name__ == "__main__":
    ingest()
