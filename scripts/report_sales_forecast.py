"""Score the saved sales forecast on the two test years and save a chart.

Run from the repository root:

    uv run --project data/pipelines/sales_forecast python scripts/report_sales_forecast.py

The saved model is not retrained. Each test month is scored with the actual
sales of earlier months only, including earlier months inside 2024 and 2025.
The month being scored is not an input. This is not a single forecast made
in December 2023 and then rolled forward without the actuals.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
_METRICS_PATH = _ROOT / "data" / "pipelines" / "sales_forecast_metrics.py"
_TRAIN_PATH = _ROOT / "scripts" / "train_sales_forecast.py"


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


metrics = _load("brasaland_sales_forecast_metrics", _METRICS_PATH)
train = _load("brasaland_sales_forecast_train", _TRAIN_PATH)

MODEL_PATH = train.MODEL_PATH
OUTPUT_DIR = MODEL_PATH.parent
JSON_PATH = OUTPUT_DIR / "sales_forecast_test_metrics.json"
MARKDOWN_PATH = OUTPUT_DIR / "sales_forecast_test_metrics.md"
FIGURE_PATH = OUTPUT_DIR / "sales_forecast_test_years.png"


def _trailing_mean(frame: pd.DataFrame) -> pd.Series:
    ordered = frame.sort_values("month")
    trailing = ordered["revenue_usd"].shift(1).rolling(12, min_periods=12).mean()
    return pd.Series(trailing.to_numpy(), index=ordered["month"].to_numpy())


def _test_predictions(payload: dict) -> pd.DataFrame:
    observed, holdout = train.phase1.split_chronological(train.phase1.load_sales())
    history = pd.concat([observed, holdout], ignore_index=True)
    table = train.training_frame(history, payload["scaler"])
    scored = table.loc[table["month"].isin(set(holdout["month"]))].sort_values("month")
    if len(scored) != len(holdout):
        raise RuntimeError("A test month is missing from the scored table")
    if set(scored["month"]).intersection(set(observed["month"])):
        raise RuntimeError("A training month was included in the scored table")

    baseline = scored["month"].map(_trailing_mean(history)).to_numpy(dtype=float)
    actual_by_month = pd.Series(holdout["revenue_usd"].to_numpy(), index=holdout["month"].to_numpy())
    actual = scored["month"].map(actual_by_month).to_numpy(dtype=float)
    if not np.allclose(actual, scored[train.TARGET_COLUMN].to_numpy(dtype=float) * baseline):
        raise RuntimeError("Test revenue does not match the seasonal index times its baseline")

    predicted_index = payload["model"].predict(scored.loc[:, list(payload["feature_columns"])])
    low_q, high_q = payload["training_residual_quantiles_10_90"]
    return pd.DataFrame(
        {
            "month": scored["month"].to_numpy(),
            "actual_usd": actual,
            "predicted_usd": predicted_index * baseline,
            "low_usd": (predicted_index + low_q) * baseline,
            "high_usd": (predicted_index + high_q) * baseline,
        }
    )


def _coverage(frame: pd.DataFrame) -> float:
    inside = (frame["actual_usd"] >= frame["low_usd"]) & (frame["actual_usd"] <= frame["high_usd"])
    return float(inside.mean())


def _save_figure(frame: pd.DataFrame) -> None:
    fig, axis = plt.subplots(figsize=(10, 5.5))
    axis.fill_between(
        frame["month"],
        frame["low_usd"],
        frame["high_usd"],
        color="#f4a261",
        alpha=0.35,
        label="Likely range",
    )
    axis.plot(frame["month"], frame["actual_usd"], color="#1d3557", linewidth=2, label="Actual sales")
    axis.plot(frame["month"], frame["predicted_usd"], color="#e76f51", linewidth=2, label="Forecast")
    axis.set_xlim(frame["month"].min() - pd.Timedelta(days=15), frame["month"].max() + pd.Timedelta(days=15))
    axis.set_title("Brasaland monthly sales, 2024 and 2025")
    axis.set_xlabel("Month")
    axis.set_ylabel("Monthly sales (USD)")
    axis.legend(frameon=False)
    axis.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _position: f"{value:,.0f}"))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURE_PATH, dpi=150)
    plt.close(fig)


def _markdown(results: dict) -> str:
    mse = results["mse_usd2"]
    typical = results["root_mean_squared_error_usd"]
    percent = results["mean_absolute_percentage_error"] * 100
    psi = results["psi"]
    gini = results["gini"]
    k2 = results["k2_score"]
    coverage = results["band_coverage"] * 100
    if psi >= metrics.PSI_LARGE:
        psi_sentence = (
            f"PSI is {psi:.3f}. That is above 0.25, the usual line for a large shift. "
            f"{results['test_months_above_training_upper_quartile']} of the {results['test_months']} "
            "test months are above the training years' upper quartile, and "
            f"{results['test_months_above_training_max']} are above the highest training month. "
            "The dollar level moved up with the growth already described in the context file. "
            "The context file says a high PSI is a reason to review retraining, and that flag stands. "
            "It is a shift in level, not a claim that the forecast missed the December peaks."
        )
    elif psi >= metrics.PSI_MODERATE:
        psi_sentence = (
            f"PSI is {psi:.3f}. That sits between 0.10 and 0.25, a moderate shift in the "
            "sales distribution. It is not a small change, and it is not a break."
        )
    else:
        psi_sentence = (
            f"PSI is {psi:.3f}. That is under 0.10, so the shape of monthly sales in the "
            "test years is close to the training years."
        )
    return "\n".join(
        [
            "# Brasaland sales forecast on the test years",
            "",
            "Scored months: January 2024 through December 2025. The model was not retrained.",
            "",
            "## Scores",
            "",
            f"- MSE: {mse:,.0f} USD squared (typical miss about {typical:,.0f} USD, average absolute miss {percent:.1f}% of that month's sales)",
            f"- PSI: {psi:.3f}",
            f"- Gini: {gini:.3f}",
            f"- K2 Score: {k2:.3f}",
            f"- Likely-range coverage: {coverage:.1f}% of the 24 test months",
            "",
            "## What Finance can read",
            "",
            (
                f"On the two most recent years, the forecast is off by about {typical:,.0f} USD "
                f"in a typical month, which is about {percent:.1f}% of that month's sales. "
                f"K2 Score is {k2:.3f}: that is the share of the ups and downs captured versus "
                "just guessing the average test month. "
                f"Gini is {gini:.3f}: that is how well the forecast ranks busier months above quieter ones, "
                "where 1 is a perfect ranking and 0 is no better than chance. "
                + psi_sentence
                + f" The shaded band on the chart covered {coverage:.1f}% of the actual months. "
                "The band is the model's usual miss from the training years, moved onto each forecast. "
                "It was not widened or narrowed after seeing 2024 and 2025."
            ),
            "",
            "## Definitions used",
            "",
            "The context file names these scores and does not give formulas. The formulas below are assumptions.",
            "",
            "- MSE is the average squared dollar miss on the test months.",
            "- The percentage next to it is the average absolute miss divided by actual sales.",
            "- PSI compares the distribution of actual monthly sales in the training years with the test years. It is not a training accuracy score.",
            "- Gini is the normalized rank agreement between the forecast and actual sales on the test months.",
            "- K2 Score is the coefficient of determination on the test months. The project screenshot calls this slot R2 Score. The name kept here is K2 Score.",
            "- The shaded band adds the 10th and 90th percentile of the training out-of-fold residual on the seasonal index to the forecast, then converts back to dollars with the previous 12 months of actual sales.",
            "",
            f"Figure: `{FIGURE_PATH.relative_to(_ROOT)}`",
            "",
        ]
    )


def main() -> None:
    payload = joblib.load(MODEL_PATH)
    frame = _test_predictions(payload)
    actual = frame["actual_usd"].to_numpy()
    predicted = frame["predicted_usd"].to_numpy()
    observed, holdout = train.phase1.split_chronological(train.phase1.load_sales())
    training_upper_quartile = float(np.quantile(observed["revenue_usd"], 0.75))
    training_max = float(observed["revenue_usd"].max())
    test_revenue = holdout["revenue_usd"].to_numpy()
    psi = metrics.population_stability_index(observed["revenue_usd"].to_numpy(), test_revenue)
    results = {
        "test_start": str(frame["month"].min().date()),
        "test_end": str(frame["month"].max().date()),
        "test_months": int(len(frame)),
        "mse_usd2": metrics.mean_squared_error_usd(actual, predicted),
        "root_mean_squared_error_usd": float(np.sqrt(metrics.mean_squared_error_usd(actual, predicted))),
        "mean_absolute_percentage_error": metrics.mean_absolute_percentage_error(actual, predicted),
        "psi": psi,
        "gini": metrics.normalized_gini(actual, predicted),
        "k2_score": metrics.k2_score(actual, predicted),
        "band_method": "training out-of-fold seasonal-index residual quantiles, 10th and 90th, times the previous 12-month mean",
        "band_residual_quantiles_10_90": [float(value) for value in payload["training_residual_quantiles_10_90"]],
        "band_coverage": _coverage(frame),
        "test_months_above_training_upper_quartile": int((test_revenue > training_upper_quartile).sum()),
        "test_months_above_training_max": int((test_revenue > training_max).sum()),
        "assumptions": [
            "PSI, Gini, and K2 Score have no formula in CONTEXT-company.md or the repo metric notes.",
            "K2 Score is computed as the coefficient of determination. The screenshot names R2 Score in this slot.",
            "PSI uses training-year actual sales as the reference distribution and test-year actual sales as the current distribution.",
            "PSI cut points 0.10 and 0.25 are the usual industry reading, not a Brasaland rule.",
            "Gini is the normalized Gini of actual sales ordered by the forecast.",
        ],
    }
    _save_figure(frame)
    JSON_PATH.write_text(json.dumps(results, indent=2) + "\n")
    MARKDOWN_PATH.write_text(_markdown(results))
    print(f"mse_usd2 {results['mse_usd2']:.2f}")
    print(f"root_mean_squared_error_usd {results['root_mean_squared_error_usd']:.2f}")
    print(f"mean_absolute_percentage_error {results['mean_absolute_percentage_error']:.6f}")
    print(f"psi {results['psi']:.6f}")
    print(f"gini {results['gini']:.6f}")
    print(f"k2_score {results['k2_score']:.6f}")
    print(f"band_coverage {results['band_coverage']:.6f}")
    print(f"saved {JSON_PATH}")
    print(f"saved {MARKDOWN_PATH}")
    print(f"saved {FIGURE_PATH}")


if __name__ == "__main__":
    main()
