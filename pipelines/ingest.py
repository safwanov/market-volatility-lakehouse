"""Bronze layer: raw OHLCV from Yahoo Finance -> append-only Parquet, partitioned by ticker."""
import datetime as dt
import pandas as pd
import yfinance as yf
from pipelines.config import BRONZE, TICKERS


def ingest(start: str = "2018-01-01") -> None:
    end = dt.date.today().isoformat()
    for t in TICKERS:
        df = yf.download(t, start=start, end=end, auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index().rename(columns=lambda c: str(c).lower().replace(" ", "_"))
        df["ticker"] = t
        df["ingested_at"] = pd.Timestamp.now(tz="UTC")
        out = BRONZE / f"ticker={t}"
        out.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out / f"{end}.parquet", index=False)  # one file per run date = idempotent re-runs
        print(f"[bronze] {t}: {len(df)} rows")


if __name__ == "__main__":
    ingest()
