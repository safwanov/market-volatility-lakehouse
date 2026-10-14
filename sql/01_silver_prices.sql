-- Silver: typed, filtered, deduplicated (latest ingestion wins per ticker/date)
CREATE OR REPLACE TABLE silver_prices AS
SELECT ticker, CAST(date AS DATE) AS date, open, high, low, close, adj_close, volume
FROM read_parquet('{ROOT}/data/bronze/*/*.parquet')
WHERE close IS NOT NULL AND close > 0
QUALIFY ROW_NUMBER() OVER (PARTITION BY ticker, date ORDER BY ingested_at DESC) = 1;
