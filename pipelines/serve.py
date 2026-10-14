"""Serving: Ridge + RandomForest ensemble forecasts volatility -> Inverse Volatility Weighting."""
import json
import duckdb
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from pipelines.config import DB, SERVING, TICKERS

FEATS = ["ret", "vol_5d", "vol_21d", "range_pct", "vol_ratio"]
TARGET = "target_vol_5d_fwd"


def run() -> dict:
    con = duckdb.connect(str(DB), read_only=True)
    mae, forecast = {}, {}
    for t in TICKERS:
        df = con.execute("SELECT * FROM gold_features WHERE ticker = ? ORDER BY date", [t]).df()
        labelled = df.dropna(subset=[TARGET])
        cut = int(len(labelled) * 0.8)
        tr, te = labelled.iloc[: cut - 5], labelled.iloc[cut:]  # chronological split + 5-day gap (target overlap)
        models = {"ridge": Ridge(alpha=1.0), "rf": RandomForestRegressor(300, max_depth=6, random_state=42, n_jobs=-1)}
        preds = {}
        for n, m in models.items():
            m.fit(tr[FEATS], tr[TARGET])
            preds[n] = m.predict(te[FEATS])
        preds["ensemble"] = (preds["ridge"] + preds["rf"]) / 2
        mae[t] = {n: round(float(mean_absolute_error(te[TARGET], p)), 4) for n, p in preds.items()}
        last = df[FEATS].iloc[[-1]]
        forecast[t] = float(np.mean([m.predict(last)[0] for m in models.values()]))
    inv = {t: 1 / v for t, v in forecast.items()}
    weights = {t: round(w / sum(inv.values()), 4) for t, w in inv.items()}
    out = {"mae_test": mae, "forecast_vol_5d": forecast, "weights": weights}
    SERVING.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    run()
