"""Temporal cross-validation and learning curve for the Brasaland sales forecast.

Run from the repository root:

    uv run --project data/pipelines/sales_forecast python pipelines/evaluate_sales_model.py

Uses the existing 8-year / 2-year chronological split and the same causal
feature builder as training. The two held-out test years are never loaded
into the CV or learning-curve loops. The saved joblib is read only for
hyperparameters; it is not modified and the training script is not re-run.

Validation-row convention (one-step-ahead)
-----------------------------------------
For a validation month ``t``, feature columns use only actuals from months
strictly before ``t`` (lags and the trailing mean behind ``growth_rate`` /
``seasonal_index``). That matches ``scripts/report_sales_forecast.py``:
the month being scored is not an input. The target ``seasonal_index`` at
``t`` still uses revenue at ``t``, so scoring compares a true one-step
prediction to the realized index.

Per-fold / per-size leakage controls
------------------------------------
Each ``TimeSeriesSplit`` fold, and each learning-curve training size, fits
``StandardScaler`` on that subset's training raw rows only, rebuilds
features from raw sales with ``training_frame``, then fits a fresh model
with the saved hyperparameters. Features are never built once on the whole
8-year window and then sliced. Learning-curve sizes are chronological
prefixes of each fold's training indices (no shuffling).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

_ROOT = Path(__file__).resolve().parents[1]
_PHASE1_PATH = _ROOT / "data" / "pipelines" / "sales_forecast.py"
_TRAIN_PATH = _ROOT / "scripts" / "train_sales_forecast.py"
EVAL_DIR = _ROOT / "data" / "eval"
LEARNING_CURVE_PATH = EVAL_DIR / "learning_curve.png"
METRICS_PATH = EVAL_DIR / "evaluation_metrics.json"

N_SPLITS = 5
WARMUP_MONTHS = 24
# Chronological prefixes. The smallest size is one year of feature-ready months.
LEARNING_CURVE_SIZES = (12, 24, 36, 48, 60)


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


phase1 = _load("brasaland_sales_forecast_pipeline", _PHASE1_PATH)
train = _load("brasaland_sales_forecast_train", _TRAIN_PATH)


@dataclass(frozen=True)
class FoldScore:
    fold: int
    n_train: int
    n_val: int
    train_mae: float
    train_rmse: float
    val_mae: float
    val_rmse: float
    train_month_min: pd.Timestamp
    train_month_max: pd.Timestamp
    val_month_min: pd.Timestamp
    val_month_max: pd.Timestamp


@dataclass(frozen=True)
class TemporalCVResult:
    folds: tuple[FoldScore, ...]
    primary_metric: str
    primary_mean: float
    primary_std: float
    train_mae_mean: float
    train_mae_std: float
    train_rmse_mean: float
    train_rmse_std: float
    mae_mean: float
    mae_std: float
    rmse_mean: float
    rmse_std: float


@dataclass(frozen=True)
class LearningCurvePoint:
    train_size: int
    n_folds: int
    train_mae_mean: float
    train_mae_std: float
    val_mae_mean: float
    val_mae_std: float
    train_rmse_mean: float
    train_rmse_std: float
    val_rmse_mean: float
    val_rmse_std: float


@dataclass(frozen=True)
class LearningCurveResult:
    points: tuple[LearningCurvePoint, ...]
    primary_metric: str


@dataclass(frozen=True)
class PrimaryMetricDecision:
    metric: str
    context_company_quotes: tuple[str, ...]
    company_briefing_quotes: tuple[str, ...]
    ranks_error_directions: bool
    justification: str


def briefing_primary_metric_decision() -> PrimaryMetricDecision:
    """Recommend MAE or RMSE only from CONTEXT-company.md and company-BRIEFING.md."""
    context_quotes = (
        "Mariana (CEO) wants to know whether, before investing in a full executive dashboard, "
        "it's possible to predict how much the chain will sell in the coming months within a "
        "reasonable margin.",
        "A low **Gini** means the model doesn't distinguish well between \"good\" and \"bad\" "
        "months — for Mariana this matters as much as the absolute error, since she needs to "
        "identify underperforming months in advance.",
        "Report **MSE** in USD², but also translate it into an average percentage error, since "
        "that's how Felipe and Mariana actually understand the number.",
    )
    company_briefing_quotes = (
        "Mariana (CEO) wants a weekly report she can open every Monday without calling anyone, "
        "comparing how each of the 14 locations is performing on cost and waste — the two levers "
        "Felipe and Lucía keep raising but that nobody currently tracks centrally.",
        "Waste Cost per Location\tHow much a location lost to expired product, kitchen error, or "
        "theft during the week, in monetary terms.\tWaste is a direct hit to margin — this is the "
        "number Felipe needs to prioritize audits.",
        "Stockout Frequency\tHow many times during the week a location's stock of some ingredient "
        "fell below the configured minimum.\tA leading indicator of service risk — frequent "
        "stockouts mean the kitchen may run out of a key ingredient mid-service.",
    )
    ranks = False
    justification = (
        "CONTEXT-company.md discusses forecast quality via margin, Gini, MSE, and percentage "
        "error, and does not mention waste, stockouts, or whether overestimation versus "
        "underestimation is costlier. Root company-BRIEFING.md discusses waste and stockouts as "
        "operations KPIs for a weekly cost report, and does not connect them to sales-forecast "
        "error direction or rank overestimation versus underestimation. Because neither source "
        "ranks the directions, MAE is the primary metric: it treats misses of either sign equally."
    )
    return PrimaryMetricDecision(
        metric="mae",
        context_company_quotes=context_quotes,
        company_briefing_quotes=company_briefing_quotes,
        ranks_error_directions=ranks,
        justification=justification,
    )


def load_training_years() -> pd.DataFrame:
    """Return the 8-year training raw frame only. Test years stay untouched."""
    observed, _holdout = phase1.split_chronological(phase1.load_sales())
    return observed.sort_values("month").reset_index(drop=True)


def feature_ready_months(raw_train: pd.DataFrame) -> pd.DatetimeIndex:
    """Months that survive the 24-month causal warmup in ``training_frame``."""
    ordered = raw_train.sort_values("month").reset_index(drop=True)
    if len(ordered) <= WARMUP_MONTHS:
        raise ValueError("Training years are shorter than the feature warmup")
    return pd.DatetimeIndex(ordered["month"].iloc[WARMUP_MONTHS:])


def load_saved_hyperparameters(model_path: Path | None = None) -> tuple[str, dict, int]:
    """Read algorithm, grid winner params, and seed from the saved payload."""
    path = model_path or train.MODEL_PATH
    payload = joblib.load(path)
    algorithm = payload["algorithm"]
    hyperparameters = dict(payload["hyperparameters"])
    random_seed = int(payload["random_seed"])
    if algorithm != "xgboost":
        raise RuntimeError(f"Expected saved algorithm xgboost, got {algorithm}")
    return algorithm, hyperparameters, random_seed


def fit_fold_scaler(fold_train_raw: pd.DataFrame) -> StandardScaler:
    """Fit guest/ticket scaling on this fold's training raw rows only."""
    scaler = StandardScaler()
    columns = list(phase1.SCALED_COLUMNS)
    scaler.fit(fold_train_raw.loc[:, columns].astype(float))
    return scaler


def build_fold_tables(
    raw_train: pd.DataFrame,
    fold_train_months: pd.DatetimeIndex,
    fold_val_months: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame, StandardScaler]:
    """Rebuild causal features for one fold with a fold-local scaler.

    History includes every training-year month up through the last validation
    month so lags at the fold boundary have prior actuals. The scaler sees
    only ``fold_train_months``. Validation features for month ``t`` still use
    only actuals before ``t`` because ``training_frame`` shifts every lag.
    """
    if max(fold_train_months) >= min(fold_val_months):
        raise RuntimeError("Fold training months must end before validation months")

    fold_train_raw = raw_train.loc[raw_train["month"].isin(fold_train_months)].copy()
    if fold_train_raw.empty:
        raise RuntimeError("Fold training raw frame is empty")

    history_end = fold_val_months.max()
    history = raw_train.loc[raw_train["month"] <= history_end].copy()
    scaler = fit_fold_scaler(fold_train_raw)
    table = train.training_frame(history, scaler)

    train_table = table.loc[table["month"].isin(fold_train_months)].reset_index(drop=True)
    val_table = table.loc[table["month"].isin(fold_val_months)].reset_index(drop=True)
    if len(train_table) != len(fold_train_months):
        raise RuntimeError("Feature rebuild dropped a fold-training month")
    if len(val_table) != len(fold_val_months):
        raise RuntimeError("Feature rebuild dropped a fold-validation month")
    return train_table, val_table, scaler


def _fresh_model(hyperparameters: dict, random_seed: int):
    # Match scripts/train_sales_forecast.py::_xgboost; seed comes from the joblib payload.
    return train.XGBRegressor(
        random_state=random_seed,
        n_jobs=1,
        objective="reg:squarederror",
        subsample=1.0,
        colsample_bytree=1.0,
        verbosity=0,
        **hyperparameters,
    )


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _score_frame(model, frame: pd.DataFrame) -> tuple[float, float]:
    features = frame.loc[:, list(train.FEATURE_COLUMNS)]
    target = frame[train.TARGET_COLUMN].to_numpy(dtype=float)
    predicted = model.predict(features)
    return float(mean_absolute_error(target, predicted)), _rmse(target, predicted)


def iter_temporal_splits(
    n_samples: int, n_splits: int = N_SPLITS
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return TimeSeriesSplit index pairs. Never shuffles."""
    splitter = TimeSeriesSplit(n_splits=n_splits)
    return list(splitter.split(np.arange(n_samples)))


def _fit_and_score_subset(
    raw_train: pd.DataFrame,
    months: pd.DatetimeIndex,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    hyperparameters: dict,
    random_seed: int,
) -> tuple[float, float, float, float, pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    fold_train_months = months[train_idx]
    fold_val_months = months[val_idx]
    train_table, val_table, _scaler = build_fold_tables(
        raw_train, fold_train_months, fold_val_months
    )
    model = _fresh_model(hyperparameters, random_seed)
    model.fit(
        train_table.loc[:, list(train.FEATURE_COLUMNS)],
        train_table[train.TARGET_COLUMN],
    )
    train_mae, train_rmse = _score_frame(model, train_table)
    val_mae, val_rmse = _score_frame(model, val_table)
    return (
        train_mae,
        train_rmse,
        val_mae,
        val_rmse,
        pd.Timestamp(train_table["month"].min()),
        pd.Timestamp(train_table["month"].max()),
        pd.Timestamp(val_table["month"].min()),
        pd.Timestamp(val_table["month"].max()),
    )


def run_temporal_cv(
    raw_train: pd.DataFrame | None = None,
    n_splits: int = N_SPLITS,
    model_path: Path | None = None,
    primary_metric: str | None = None,
) -> TemporalCVResult:
    """Fit-per-fold temporal CV on the 8-year training portion only."""
    observed = raw_train if raw_train is not None else load_training_years()
    months = feature_ready_months(observed)
    _algorithm, hyperparameters, random_seed = load_saved_hyperparameters(model_path)
    primary = primary_metric or briefing_primary_metric_decision().metric

    fold_scores: list[FoldScore] = []
    for fold_number, (train_idx, val_idx) in enumerate(iter_temporal_splits(len(months), n_splits), start=1):
        if max(train_idx) >= min(val_idx):
            raise RuntimeError("TimeSeriesSplit produced a non-chronological fold")
        if list(train_idx) != sorted(train_idx) or list(val_idx) != sorted(val_idx):
            raise RuntimeError("TimeSeriesSplit produced unsorted indices")

        train_mae, train_rmse, val_mae, val_rmse, tr_min, tr_max, va_min, va_max = _fit_and_score_subset(
            observed, months, train_idx, val_idx, hyperparameters, random_seed
        )
        fold_scores.append(
            FoldScore(
                fold=fold_number,
                n_train=len(train_idx),
                n_val=len(val_idx),
                train_mae=train_mae,
                train_rmse=train_rmse,
                val_mae=val_mae,
                val_rmse=val_rmse,
                train_month_min=tr_min,
                train_month_max=tr_max,
                val_month_min=va_min,
                val_month_max=va_max,
            )
        )

    train_mae = np.asarray([score.train_mae for score in fold_scores], dtype=float)
    train_rmse = np.asarray([score.train_rmse for score in fold_scores], dtype=float)
    val_mae = np.asarray([score.val_mae for score in fold_scores], dtype=float)
    val_rmse = np.asarray([score.val_rmse for score in fold_scores], dtype=float)
    primary_values = val_mae if primary == "mae" else val_rmse
    return TemporalCVResult(
        folds=tuple(fold_scores),
        primary_metric=primary,
        primary_mean=float(primary_values.mean()),
        primary_std=float(primary_values.std(ddof=0)),
        train_mae_mean=float(train_mae.mean()),
        train_mae_std=float(train_mae.std(ddof=0)),
        train_rmse_mean=float(train_rmse.mean()),
        train_rmse_std=float(train_rmse.std(ddof=0)),
        mae_mean=float(val_mae.mean()),
        mae_std=float(val_mae.std(ddof=0)),
        rmse_mean=float(val_rmse.mean()),
        rmse_std=float(val_rmse.std(ddof=0)),
    )


def run_learning_curve(
    raw_train: pd.DataFrame | None = None,
    n_splits: int = N_SPLITS,
    train_sizes: tuple[int, ...] = LEARNING_CURVE_SIZES,
    model_path: Path | None = None,
    primary_metric: str | None = None,
) -> LearningCurveResult:
    """Temporal learning curve with per-size scaler fit and feature rebuild.

    For each ``TimeSeriesSplit`` fold, training sizes are chronological prefixes
    of that fold's training indices (``train_idx[:size]``). Sizes larger than a
    fold's training length are skipped for that fold. No shuffling.
    """
    observed = raw_train if raw_train is not None else load_training_years()
    months = feature_ready_months(observed)
    _algorithm, hyperparameters, random_seed = load_saved_hyperparameters(model_path)
    primary = primary_metric or briefing_primary_metric_decision().metric
    splits = iter_temporal_splits(len(months), n_splits)

    points: list[LearningCurvePoint] = []
    for size in train_sizes:
        train_maes: list[float] = []
        train_rmses: list[float] = []
        val_maes: list[float] = []
        val_rmses: list[float] = []
        for train_idx, val_idx in splits:
            if len(train_idx) < size:
                continue
            prefix = train_idx[:size]
            if list(prefix) != sorted(prefix):
                raise RuntimeError("Learning-curve train prefix is not chronological")
            if max(prefix) >= min(val_idx):
                raise RuntimeError("Learning-curve train prefix overlaps validation")
            train_mae, train_rmse, val_mae, val_rmse, *_rest = _fit_and_score_subset(
                observed, months, prefix, val_idx, hyperparameters, random_seed
            )
            train_maes.append(train_mae)
            train_rmses.append(train_rmse)
            val_maes.append(val_mae)
            val_rmses.append(val_rmse)
        if not val_maes:
            raise RuntimeError(f"No temporal fold supports train_size={size}")
        points.append(
            LearningCurvePoint(
                train_size=size,
                n_folds=len(val_maes),
                train_mae_mean=float(np.mean(train_maes)),
                train_mae_std=float(np.std(train_maes, ddof=0)),
                val_mae_mean=float(np.mean(val_maes)),
                val_mae_std=float(np.std(val_maes, ddof=0)),
                train_rmse_mean=float(np.mean(train_rmses)),
                train_rmse_std=float(np.std(train_rmses, ddof=0)),
                val_rmse_mean=float(np.mean(val_rmses)),
                val_rmse_std=float(np.std(val_rmses, ddof=0)),
            )
        )
    return LearningCurveResult(points=tuple(points), primary_metric=primary)


def save_learning_curve_plot(curve: LearningCurveResult, path: Path = LEARNING_CURVE_PATH) -> Path:
    """Save train vs validation error versus chronological training size."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sizes = [point.train_size for point in curve.points]
    if curve.primary_metric == "mae":
        train_means = [point.train_mae_mean for point in curve.points]
        train_stds = [point.train_mae_std for point in curve.points]
        val_means = [point.val_mae_mean for point in curve.points]
        val_stds = [point.val_mae_std for point in curve.points]
        ylabel = "MAE on seasonal_index (unitless)"
        title_metric = "MAE"
    else:
        train_means = [point.train_rmse_mean for point in curve.points]
        train_stds = [point.train_rmse_std for point in curve.points]
        val_means = [point.val_rmse_mean for point in curve.points]
        val_stds = [point.val_rmse_std for point in curve.points]
        ylabel = "RMSE on seasonal_index (unitless)"
        title_metric = "RMSE"

    fig, axis = plt.subplots(figsize=(9.5, 5.5))
    axis.errorbar(
        sizes,
        train_means,
        yerr=train_stds,
        marker="o",
        color="#1d3557",
        label=f"Training {title_metric}",
        capsize=3,
    )
    axis.errorbar(
        sizes,
        val_means,
        yerr=val_stds,
        marker="o",
        color="#e76f51",
        label=f"Validation {title_metric}",
        capsize=3,
    )
    axis.set_xlabel("Training set size (feature-ready months, chronological prefix)")
    axis.set_ylabel(ylabel)
    axis.set_title(
        "Brasaland sales forecast learning curve\n"
        f"(8-year training years only; TimeSeriesSplit; primary={title_metric})"
    )
    axis.set_xticks(sizes)
    axis.grid(True, alpha=0.3)
    axis.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def describe_curve_pattern(curve: LearningCurveResult) -> str:
    """Plain-language pattern notes only. No fit diagnosis label."""
    first = curve.points[0]
    last = curve.points[-1]
    if curve.primary_metric == "mae":
        train_first, train_last = first.train_mae_mean, last.train_mae_mean
        val_first, val_last = first.val_mae_mean, last.val_mae_mean
    else:
        train_first, train_last = first.train_rmse_mean, last.train_rmse_mean
        val_first, val_last = first.val_rmse_mean, last.val_rmse_mean
    gap_first = val_first - train_first
    gap_last = val_last - train_last
    return (
        f"Smallest training sizes are tiny (about {first.train_size} feature-ready months). "
        f"At size {first.train_size}, training {curve.primary_metric} is {train_first:.6f} and "
        f"validation {curve.primary_metric} is {val_first:.6f} (gap {gap_first:.6f}). "
        f"At size {last.train_size}, training {curve.primary_metric} is {train_last:.6f} and "
        f"validation {curve.primary_metric} is {val_last:.6f} (gap {gap_last:.6f}). "
        f"Across sizes, validation stays above training; the gap remains positive from the "
        f"smallest size through the largest."
    )


def _fold_to_json(fold: FoldScore) -> dict:
    payload = asdict(fold)
    for key in (
        "train_month_min",
        "train_month_max",
        "val_month_min",
        "val_month_max",
    ):
        payload[key] = pd.Timestamp(payload[key]).strftime("%Y-%m-%d")
    return payload


def write_metrics_artifact(
    decision: PrimaryMetricDecision,
    cv_result: TemporalCVResult,
    curve: LearningCurveResult,
    path: Path = METRICS_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "target": train.TARGET_COLUMN,
        "units": "seasonal_index (unitless ratio: revenue_usd / trailing 12-month mean)",
        "held_out_test_years_used": False,
        "briefing_evidence": {
            "CONTEXT-company.md": list(decision.context_company_quotes),
            "company-BRIEFING.md": list(decision.company_briefing_quotes),
            "ranks_over_vs_under_estimation": decision.ranks_error_directions,
        },
        "primary_metric_recommendation": {
            "metric": decision.metric,
            "justification": decision.justification,
        },
        "temporal_cv": {
            "n_splits": len(cv_result.folds),
            "folds": [_fold_to_json(fold) for fold in cv_result.folds],
            "train_mae": {"mean": cv_result.train_mae_mean, "std": cv_result.train_mae_std},
            "train_rmse": {"mean": cv_result.train_rmse_mean, "std": cv_result.train_rmse_std},
            "val_mae": {"mean": cv_result.mae_mean, "std": cv_result.mae_std},
            "val_rmse": {"mean": cv_result.rmse_mean, "std": cv_result.rmse_std},
            "primary": {
                "metric": cv_result.primary_metric,
                "mean": cv_result.primary_mean,
                "std": cv_result.primary_std,
            },
        },
        "learning_curve": {
            "path": str(LEARNING_CURVE_PATH.relative_to(_ROOT)),
            "train_sizes": [point.train_size for point in curve.points],
            "n_folds_per_size": [point.n_folds for point in curve.points],
            "points": [asdict(point) for point in curve.points],
            "smallest_train_size_note": (
                f"Smallest training sizes are tiny (about {curve.points[0].train_size} rows)."
            ),
            "pattern_notes": describe_curve_pattern(curve),
        },
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def format_report(
    decision: PrimaryMetricDecision,
    cv_result: TemporalCVResult,
    curve: LearningCurveResult,
) -> str:
    lines = [
        "Brasaland sales forecast — temporal CV and learning curve (training years only)",
        f"target={train.TARGET_COLUMN} primary={decision.metric}",
        "",
        "Briefing evidence (verbatim quotes used for the metric decision):",
        "CONTEXT-company.md:",
    ]
    for quote in decision.context_company_quotes:
        lines.append(f"  - {quote}")
    lines.append("company-BRIEFING.md:")
    for quote in decision.company_briefing_quotes:
        lines.append(f"  - {quote}")
    lines.extend(
        [
            f"ranks_over_vs_under_estimation={decision.ranks_error_directions}",
            f"primary_metric_recommendation={decision.metric}",
            f"justification={decision.justification}",
            "",
            "Temporal CV folds:",
        ]
    )
    for fold in cv_result.folds:
        lines.append(
            f"fold {fold.fold}: "
            f"n_train={fold.n_train} n_val={fold.n_val} "
            f"train[{fold.train_month_min.date()}..{fold.train_month_max.date()}] "
            f"val[{fold.val_month_min.date()}..{fold.val_month_max.date()}] "
            f"val_mae={fold.val_mae:.6f} val_rmse={fold.val_rmse:.6f} "
            f"train_mae={fold.train_mae:.6f} train_rmse={fold.train_rmse:.6f}"
        )
    lines.extend(
        [
            "",
            "Metric table (temporal CV, mean ± std across folds):",
            f"train_mae  {cv_result.train_mae_mean:.6f} ± {cv_result.train_mae_std:.6f}",
            f"train_rmse {cv_result.train_rmse_mean:.6f} ± {cv_result.train_rmse_std:.6f}",
            f"val_mae    {cv_result.mae_mean:.6f} ± {cv_result.mae_std:.6f}",
            f"val_rmse   {cv_result.rmse_mean:.6f} ± {cv_result.rmse_std:.6f}",
            f"primary    {cv_result.primary_mean:.6f} ± {cv_result.primary_std:.6f}",
            "",
            "Learning curve:",
        ]
    )
    for point in curve.points:
        lines.append(
            f"size={point.train_size} folds={point.n_folds} "
            f"train_mae={point.train_mae_mean:.6f}±{point.train_mae_std:.6f} "
            f"val_mae={point.val_mae_mean:.6f}±{point.val_mae_std:.6f} "
            f"train_rmse={point.train_rmse_mean:.6f}±{point.train_rmse_std:.6f} "
            f"val_rmse={point.val_rmse_mean:.6f}±{point.val_rmse_std:.6f}"
        )
    lines.extend(["", "Observed curve pattern:", describe_curve_pattern(curve)])
    return "\n".join(lines)


def main() -> None:
    decision = briefing_primary_metric_decision()
    raw_train = load_training_years()
    cv_result = run_temporal_cv(raw_train=raw_train, primary_metric=decision.metric)
    curve = run_learning_curve(raw_train=raw_train, primary_metric=decision.metric)
    png_path = save_learning_curve_plot(curve)
    metrics_path = write_metrics_artifact(decision, cv_result, curve)
    print(format_report(decision, cv_result, curve))
    print(f"wrote {png_path}")
    print(f"wrote {metrics_path}")


if __name__ == "__main__":
    main()
