"""Quality gate: every check is a SQL query that must return 0. Any failure stops the DAG."""
import sys
import duckdb
from pipelines.config import DB

CHECKS = {
    "no_duplicate_keys": "SELECT COUNT(*) FROM (SELECT 1 FROM silver_prices GROUP BY ticker, date HAVING COUNT(*) > 1)",
    "no_null_measures": "SELECT COUNT(*) FROM silver_prices WHERE adj_close IS NULL OR volume IS NULL",
    "valid_price_range": "SELECT COUNT(*) FROM silver_prices WHERE low <= 0 OR high < low",
    "no_extreme_returns": "SELECT COUNT(*) FROM gold_features WHERE ABS(ret) > 0.5",
    "fresh_within_7_days": "SELECT CASE WHEN MAX(date) < CURRENT_DATE - INTERVAL 7 DAY THEN 1 ELSE 0 END FROM silver_prices",
}


def run() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    failed = [n for n, q in CHECKS.items() if con.execute(q).fetchone()[0] != 0]
    for n in CHECKS:
        print(f"[quality] {'FAIL' if n in failed else 'PASS'}  {n}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run()
