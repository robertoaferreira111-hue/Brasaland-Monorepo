"""Train the Brasaland sales forecast on the first 8 years only.

Run from the repository root:

    uv run --project data/pipelines/sales_forecast python scripts/train_sales_forecast.py

The Phase 1 split is used as-is. The 2 most recent years are never fit,
scored, or used to choose hyperparameters.

Choice, and why it is not "the better algorithm" in the abstract
-----------------------------------------------------------------
The training table is small: 120 consolidated months in the file, 96 in
the first 8 years, and 72 after a 24-month warmup. Six columns describe
each month. On a table that size, a large boost search mostly memorizes
folds, so both candidates get the same four-point grid and the same
time-ordered split inside those 8 years.

Finance has to review the model. A random forest reports impurity
importance and can show one tree. Its variability range is the 10th to
90th percentile of the individual trees' predictions. That range does
not need a second model. XGBoost's gain importance is usable, but a
prediction range needs an extra construction. Tuning time is the wall
clock of each four-point grid.

Rule used here: keep each algorithm's best training-fold mean squared
error on the seasonal index. If XGBoost's error is more than 5 percent
lower, use XGBoost. Otherwise use the random forest, because the errors
are close, Finance can read a forest tree, and the forest already has a
variability range from its trees. Tuning time is measured for both grids
rather than assumed.

Measured on this file, inside the training years only (72 rows, January
2018 through December 2023, three time-ordered folds): random forest
mean squared error 0.00267246 (best grid ``n_estimators=200``,
``max_depth=5``, ``min_samples_leaf=2``), XGBoost mean squared error
0.00165595 (best grid ``n_estimators=100``, ``max_depth=3``,
``learning_rate=0.05``, ``random_state=42``). The forest grid took
several seconds and the XGBoost grid took under a second; those wall
times move a little between machines, and the errors above do not.
XGBoost is about 38 percent lower, which clears the 5 percent margin,
so this run selects XGBoost even though a forest is easier to walk
through with Finance. Gain importance on the fitted model is led by
``month_of_year`` (about 0.72) and ``index_lag_12`` (about 0.12). The
variability range saved with the model is the 10th and 90th percentile
of out-of-fold residuals on the seasonal index, about -0.045 to 0.058,
from those same training folds. It is the leftover error around the
prediction, not a score of the two holdout years. Multiplying that
index band by the trailing 12-month mean, known from past months only,
is how a later dollar range is formed. Loading XGBoost on macOS needs
the OpenMP runtime (``libomp.dylib``) on the dynamic loader path.

Trees do not extrapolate a rising revenue level. A leaf returns an
average of training targets, so a model of raw ``revenue_usd`` cannot
emit a dollar level above the 2016-2023 range. ``CONTEXT-company.md``
states the pattern as a rate, not as a dollar level: each year grows by
3 percent or 7 percent, January is 12-18 percent below the previous
year's average, December is 20-30 percent above that average, and the
other months stay within about 5 percent of the growth trend. The
target is therefore the seasonal index, current revenue divided by the
mean of the previous 12 months. That index stays inside a band the
training years already contain. A later dollar figure is the predicted
index times that trailing mean. The trailing mean is known from past
months only, so the dollar level can rise with the documented growth
without the tree inventing a higher leaf value.

Features use past months only: calendar month, last month's index, the
same month last year's index, the growth of the trailing 12-month mean
over the 12 months before that, and last month's scaled guest count and
average ticket. The Phase 1 scaler is fit on the training years only.
Same-month guests and ticket are not features, because they are part of
the month being forecast.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBRegressor

_ROOT = Path(__file__).resolve().parents[1]
_PHASE1_PATH = _ROOT / "data" / "pipelines" / "sales_forecast.py"
_SPEC = importlib.util.spec_from_file_location("brasaland_sales_forecast_pipeline", _PHASE1_PATH)
assert _SPEC is not None and _SPEC.loader is not None
phase1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = phase1
_SPEC.loader.exec_module(phase1)

FEATURE_COLUMNS = (
    "month_of_year",
    "index_lag_1",
    "index_lag_12",
    "growth_rate",
    "covers_lag_1",
    "ticket_lag_1",
)
TARGET_COLUMN = "seasonal_index"
MODEL_PATH = _ROOT / "data" / "pipelines" / "sales_forecast" / "sales_forecast_model.joblib"
CV_SPLITS = 3
RELATIVE_MARGIN = 0.05

RF_GRID = (
    {"n_estimators": 200, "max_depth": 3, "min_samples_leaf": 2},
    {"n_estimators": 200, "max_depth": 3, "min_samples_leaf": 4},
    {"n_estimators": 200, "max_depth": 5, "min_samples_leaf": 2},
    {"n_estimators": 200, "max_depth": 5, "min_samples_leaf": 4},
)
XGB_GRID = (
    {"n_estimators": 100, "max_depth": 2, "learning_rate": 0.05},
    {"n_estimators": 100, "max_depth": 2, "learning_rate": 0.1},
    {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.05},
    {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.1},
)


def training_frame(train: pd.DataFrame, scaler) -> pd.DataFrame:
    """Causal rows from the training years. The first 24 months are the warmup."""
    frame = train.sort_values("month").reset_index(drop=True)
    revenue = frame["revenue_usd"]
    trailing = revenue.shift(1).rolling(12, min_periods=12).mean()
    seasonal_index = revenue / trailing
    growth = trailing / trailing.shift(12) - 1.0
    scaled = scaler.transform(frame.loc[:, list(phase1.SCALED_COLUMNS)])
    table = pd.DataFrame(
        {
            "month": frame["month"],
            "month_of_year": frame["month"].dt.month.astype(int),
            "index_lag_1": seasonal_index.shift(1),
            "index_lag_12": seasonal_index.shift(12),
            "growth_rate": growth,
            "covers_lag_1": pd.Series(scaled[:, 0], index=frame.index).shift(1),
            "ticket_lag_1": pd.Series(scaled[:, 1], index=frame.index).shift(1),
            TARGET_COLUMN: seasonal_index,
        }
    )
    return table.dropna().reset_index(drop=True)


def _cv_mse(estimator, features: pd.DataFrame, target: pd.Series) -> float:
    splitter = TimeSeriesSplit(n_splits=CV_SPLITS)
    scores: list[float] = []
    for train_index, valid_index in splitter.split(features):
        estimator.fit(features.iloc[train_index], target.iloc[train_index])
        predicted = estimator.predict(features.iloc[valid_index])
        scores.append(float(mean_squared_error(target.iloc[valid_index], predicted)))
    return float(np.mean(scores))


def _random_forest(params: dict) -> RandomForestRegressor:
    return RandomForestRegressor(random_state=phase1.RANDOM_SEED, n_jobs=1, **params)


def _xgboost(params: dict) -> XGBRegressor:
    return XGBRegressor(
        random_state=phase1.RANDOM_SEED,
        n_jobs=1,
        objective="reg:squarederror",
        subsample=1.0,
        colsample_bytree=1.0,
        verbosity=0,
        **params,
    )


def _best_grid(factory, grid: tuple[dict, ...], features: pd.DataFrame, target: pd.Series) -> tuple[dict, float, float]:
    started = time.perf_counter()
    best_params = grid[0]
    best_score = float("inf")
    for params in grid:
        score = _cv_mse(factory(params), features, target)
        if score < best_score:
            best_score = score
            best_params = params
    return best_params, best_score, time.perf_counter() - started


def _choose(rf_mse: float, xgb_mse: float) -> str:
    if xgb_mse < rf_mse * (1.0 - RELATIVE_MARGIN):
        return "xgboost"
    return "random_forest"


def _validation_residual_quantiles(estimator, features: pd.DataFrame, target: pd.Series) -> tuple[float, float]:
    """10th and 90th percentile of time-ordered validation residuals."""
    splitter = TimeSeriesSplit(n_splits=CV_SPLITS)
    residuals: list[np.ndarray] = []
    for train_index, valid_index in splitter.split(features):
        estimator.fit(features.iloc[train_index], target.iloc[train_index])
        predicted = estimator.predict(features.iloc[valid_index])
        residuals.append(target.iloc[valid_index].to_numpy() - predicted)
    low, high = np.percentile(np.concatenate(residuals), [10, 90])
    return float(low), float(high)


def _tree_range(model: RandomForestRegressor, features: pd.DataFrame) -> np.ndarray:
    per_tree = np.vstack([tree.predict(features) for tree in model.estimators_])
    low, high = np.percentile(per_tree, [10, 90], axis=0)
    return high - low


def main() -> None:
    observed, holdout = phase1.split_chronological(phase1.load_sales())
    prepared = phase1.scale_features(observed, observed.iloc[:1].copy())
    table = training_frame(observed, prepared.scaler)
    if not set(table["month"]).isdisjoint(set(holdout["month"])):
        raise RuntimeError("Training rows include a holdout month")
    if table["month"].max() != observed["month"].max():
        raise RuntimeError("Training table does not end on the last training month")

    features = table.loc[:, list(FEATURE_COLUMNS)]
    target = table[TARGET_COLUMN]
    rf_params, rf_mse, rf_seconds = _best_grid(_random_forest, RF_GRID, features, target)
    xgb_params, xgb_mse, xgb_seconds = _best_grid(_xgboost, XGB_GRID, features, target)
    chosen = _choose(rf_mse, xgb_mse)

    if chosen == "random_forest":
        model = _random_forest(rf_params)
        hyperparameters = rf_params
        variability = "per_tree_percentiles_10_90"
    else:
        model = _xgboost(xgb_params)
        hyperparameters = xgb_params
        variability = "out_of_fold_residual_quantiles_10_90"
    model.fit(features, target)

    payload = {
        "algorithm": chosen,
        "model": model,
        "hyperparameters": hyperparameters,
        "feature_columns": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "target_definition": "revenue_usd / mean of the previous 12 months",
        "random_seed": phase1.RANDOM_SEED,
        "scaler": prepared.scaler,
        "scaled_columns": phase1.SCALED_COLUMNS,
        "training_cv_mse": {"random_forest": rf_mse, "xgboost": xgb_mse},
        "variability": variability,
    }
    if chosen == "random_forest":
        width = _tree_range(model, features)
        payload["training_index_range_width_median"] = float(np.median(width))
    else:
        low, high = _validation_residual_quantiles(_xgboost(xgb_params), features, target)
        payload["training_residual_quantiles_10_90"] = (low, high)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, MODEL_PATH)

    print(f"random_forest_hyperparameters {rf_params}")
    print(f"xgboost_hyperparameters {xgb_params}")
    print(f"algorithm {chosen}")
    print(f"training_rows {len(table)}")
    print(f"training_month_min {table['month'].min().date()}")
    print(f"training_month_max {table['month'].max().date()}")
    print(f"random_forest_cv_mse {rf_mse:.8f} seconds {rf_seconds:.3f}")
    print(f"xgboost_cv_mse {xgb_mse:.8f} seconds {xgb_seconds:.3f}")
    print(f"variability {variability}")
    if chosen == "random_forest":
        print(f"training_index_range_width_median {payload['training_index_range_width_median']:.6f}")
        importances = pd.Series(model.feature_importances_, index=FEATURE_COLUMNS).sort_values(ascending=False)
    else:
        print(f"training_residual_quantiles_10_90 {payload['training_residual_quantiles_10_90']}")
        importances = pd.Series(model.feature_importances_, index=FEATURE_COLUMNS).sort_values(ascending=False)
    print("feature_importances")
    for name, value in importances.items():
        print(f"  {name} {value:.6f}")
    print(f"saved {MODEL_PATH}")


if __name__ == "__main__":
    main()
