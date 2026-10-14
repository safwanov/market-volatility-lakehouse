-- Gold: ML-ready features. Target = realised vol of the NEXT 5 trading days.
CREATE OR REPLACE TABLE gold_features AS
WITH r AS (
  SELECT *, LN(adj_close / LAG(adj_close) OVER (PARTITION BY ticker ORDER BY date)) AS ret
  FROM silver_prices
), f AS (
  SELECT ticker, date, ret,
    STDDEV(ret) OVER (PARTITION BY ticker ORDER BY date ROWS 4 PRECEDING)  * SQRT(252) AS vol_5d,
    STDDEV(ret) OVER (PARTITION BY ticker ORDER BY date ROWS 20 PRECEDING) * SQRT(252) AS vol_21d,
    (high - low) / close AS range_pct
  FROM r
)
SELECT *, vol_5d / NULLIF(vol_21d, 0) AS vol_ratio,
       LEAD(vol_5d, 5) OVER (PARTITION BY ticker ORDER BY date) AS target_vol_5d_fwd
FROM f
WHERE vol_21d IS NOT NULL;
