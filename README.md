# Market Volatility Lakehouse

> A production-inspired **data engineering pipeline** that ingests market data, models it through a medallion architecture, validates it with quality gates, and serves volatility forecasts and portfolio weights, orchestrated by Airflow.

Engineering sequel to my final year project, where the same use case lived in a single notebook. Here the focus is the **platform around the model**.

## Architecture

```mermaid
flowchart LR
  Y[Yahoo Finance] -->|yfinance| B[(Bronze<br/>raw Parquet)]
  B -->|DuckDB SQL| S[(Silver<br/>clean, deduped)]
  S -->|window functions| G[(Gold<br/>features + target)]
  G --> Q{Quality gate<br/>5 checks}
  Q -->|pass| M[Ridge + RF<br/>ensemble]
  M --> W[Inverse-Vol<br/>weights JSON]
  A[[Airflow DAG<br/>weekdays 22:00 UTC]] -.orchestrates.-> B
```

| Layer | Tech | Responsibility |
|---|---|---|
| Bronze | Python, yfinance, Parquet | Raw, append-only, partitioned by ticker, stamped with `ingested_at` |
| Silver | DuckDB SQL | Typing, filtering, dedup via `QUALIFY ROW_NUMBER()` (latest ingestion wins) |
| Gold | DuckDB window functions | Rolling 5d/21d annualised vol, range, vol ratio, forward 5d target |
| Quality | SQL assertions | Uniqueness, nulls, price sanity, outlier returns, freshness. Failure halts the DAG |
| Serving | scikit-learn | Chronological split with leakage gap, Ridge + Random Forest ensemble, Inverse Volatility Weighting |
| Orchestration | Airflow (Docker) | `bronze >> silver_gold >> quality_gate >> serve`, 2 retries with backoff, weekdays at 22:00 UTC |
| CI | GitHub Actions + ruff | Lint and compile on every push |

## Quickstart

```bash
make install
make run          # ingest -> transform -> quality -> serve  (writes data/serving.json)
make up           # Airflow UI on http://localhost:8080
```
## Results

Sample output of `make run` (`data/serving.json`), test set is the last 20% of history, chronological split with a 5-day gap.

**Forecast error (MAE on 5-day forward annualised volatility, lower is better)**

| Ticker | Ridge | Random Forest | Ensemble |
|---|---|---|---|
| TSLA | **0.1861** | 0.1897 | 0.1873 |
| SPY | **0.0558** | 0.0588 | 0.0563 |

**Latest forecast and allocation (Inverse Volatility Weighting)**

| Ticker | Forecast vol (5d, annualised) | Portfolio weight |
|---|---|---|
| TSLA | 45.4% | 16.7% |
| SPY | 9.1% | 83.3% |

**Takeaways**

- On this single chronological split, Ridge and Random Forest are within about 2-5% of each other (e.g. TSLA: 0.1861 vs 0.1897). That gap is too small to call a winner; it needs more tickers and several time splits.
- Inverse-volatility weighting gives more weight to calmer assets by construction (SPY gets about 5x TSLA's weight here). This shows the allocation step works. It is not evidence that the forecasts are accurate.
- Not yet verified: whether the models beat a naive persistence baseline (see Roadmap).

## Design decisions

- **SQL for transforms, Python for I/O and ML**: transformations stay declarative, versionable and testable in the warehouse.
- **Idempotent ingestion**: one Parquet file per run date; Silver deduplicates, so re-runs never create duplicates.
- **Quality gate before serving**: bad data never reaches the model.
- **No look-ahead**: time-ordered split and a 5-day gap matching the target horizon.

## Roadmap

- [ ] Unit tests on synthetic data
- [ ] Migrate SQL to dbt models + tests
- [ ] Incremental loads instead of full refresh
- [ ] Dashboard on top of `serving.json`
- [ ] Data lineage and run metadata table
- [ ] Naive persistence baseline to benchmark the models

## Author

**safwanov**, Data Engineering and ML.
