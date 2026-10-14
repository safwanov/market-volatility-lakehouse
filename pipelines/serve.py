"""Serving: Ridge + RandomForest ensemble forecasts volatility -> Inverse Volatility Weighting.

Evaluation: chronological 80/20 split with a 5-row gap (the target looks 5 days ahead).
Every model is compared with two naive baselines that need no model at all.
"""

import json

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from pipelines.config import DB, SERVING, TICKERS

FEATS = ["ret", "vol_5d", "vol_21d", "range_pct", "vol_ratio"]
TARGET = "target_vol_5d_fwd"
GAP = 5
MIN_VOL = 0.01  # floor (1% annualised): a bad prediction can never give negative or infinite weights


def make_models() -> dict:
    # Ridge needs features on a similar scale, so they are standardised first.
    return {
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "rf": RandomForestRegressor(300, max_depth=6, random_state=42, n_jobs=-1),
    }


def evaluate(df) -> dict:
    """MAE on the test period for each model and for two naive baselines."""
    labelled = df.dropna(subset=[TARGET])
    cut = int(len(labelled) * 0.8)
    tr, te = labelled.iloc[: cut - GAP], labelled.iloc[cut:]  # chronological split + gap (target overlap)
    preds = {}
    for name, model in make_models().items():
        model.fit(tr[FEATS], tr[TARGET])
        preds[name] = model.predict(te[FEATS])
    preds["ensemble"] = (preds["ridge"] + preds["rf"]) / 2
    preds["naive_5d"] = te["vol_5d"].to_numpy()  # baseline: next week looks like this week
    preds["naive_21d"] = te["vol_21d"].to_numpy()  # baseline: next week looks like the last month
    return {n: round(float(mean_absolute_error(te[TARGET], p)), 4) for n, p in preds.items()}


def skill_vs_naive(mae: dict) -> float:
    """% error reduction of the ensemble vs the best naive baseline (positive = the model adds value)."""
    best_naive = min(mae["naive_5d"], mae["naive_21d"])
    return round(100 * (1 - mae["ensemble"] / best_naive), 1)


def forecast_next(df) -> float:
    """Final forecast: models are refit on ALL labelled history, so recent data is not wasted."""
    labelled = df.dropna(subset=[TARGET])
    last = df[FEATS].iloc[[-1]]
    preds = []
    for model in make_models().values():
        model.fit(labelled[FEATS], labelled[TARGET])
        preds.append(model.predict(last)[0])
    return max(float(np.mean(preds)), MIN_VOL)


def inverse_vol_weights(forecast: dict) -> dict:
    inv = {t: 1 / v for t, v in forecast.items()}
    total = sum(inv.values())
    return {t: round(w / total, 4) for t, w in inv.items()}


def run() -> dict:
    import duckdb  # imported here so the functions above can be tested without a database

    con = duckdb.connect(str(DB), read_only=True)
    try:
        frames = {
            t: con.execute("SELECT * FROM gold_features WHERE ticker = ? ORDER BY date", [t]).df()
            for t in TICKERS
        }
    finally:
        con.close()

    mae, skill, forecast = {}, {}, {}
    for t, df in frames.items():
        mae[t] = evaluate(df)
        skill[t] = skill_vs_naive(mae[t])
        forecast[t] = forecast_next(df)

    out = {
        "mae_test": mae,
        "ensemble_vs_best_naive_pct": skill,
        "forecast_vol_5d": forecast,
        "weights": inverse_vol_weights(forecast),
    }
    SERVING.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    run()
