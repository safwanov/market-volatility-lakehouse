from datetime import timedelta

import pendulum
from airflow.decorators import dag, task


@dag(
    schedule="0 22 * * 1-5",  # weekdays at 22:00 UTC, after the US market close
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,  # DuckDB accepts a single writer: never run two pipelines at once
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,  # wait longer between retries (helps with API rate limits)
    },
    tags=["finance", "lakehouse"],
)
def volatility_lakehouse():
    @task
    def bronze():
        from pipelines.ingest import ingest
        ingest()

    @task
    def silver_gold():
        from pipelines.transform import run
        run()

    @task
    def quality_gate():
        from pipelines.quality import run
        run()

    @task
    def serve():
        from pipelines.serve import run
        run()

    bronze() >> silver_gold() >> quality_gate() >> serve()


volatility_lakehouse()
