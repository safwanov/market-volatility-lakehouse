import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
BRONZE = ROOT / "data" / "bronze"
DB = ROOT / "data" / "warehouse.duckdb"
SERVING = ROOT / "data" / "serving.json"
TICKERS = ["TSLA", "SPY"]
