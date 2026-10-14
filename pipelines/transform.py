"""Silver + Gold layers: plain SQL files executed in order by DuckDB."""
import duckdb
from pipelines.config import DB, ROOT


def run() -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    for f in sorted((ROOT / "sql").glob("*.sql")):
        con.execute(f.read_text().replace("{ROOT}", str(ROOT)))
        print(f"[sql] {f.name}")


if __name__ == "__main__":
    run()
