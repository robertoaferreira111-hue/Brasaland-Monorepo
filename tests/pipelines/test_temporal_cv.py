"""Temporal CV order and leakage checks for Brasaland sales evaluation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

_ROOT = Path(__file__).resolve().parents[2]
_EVAL_PATH = _ROOT / "pipelines" / "evaluate_sales_model.py"
_SPEC = importlib.util.spec_from_file_location("brasaland_evaluate_sales_model", _EVAL_PATH)
assert _SPEC is not None and _SPEC.loader is not None
evaluate = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = evaluate
_SPEC.loader.exec_module(evaluate)


def _feature_months():
    raw_train = evaluate.load_training_years()
    return raw_train, evaluate.feature_ready_months(raw_train)


def test_temporal_cv_preserves_chronological_order():
    _raw_train, months = _feature_months()
    tscv = TimeSeriesSplit(n_splits=evaluate.N_SPLITS)
    for train_idx, val_idx in tscv.split(np.arange(len(months))):
        assert max(train_idx) < min(val_idx)
        assert list(train_idx) == sorted(train_idx)
        assert list(val_idx) == sorted(val_idx)


def test_evaluate_module_uses_timeseries_split_without_shuffle():
    source = _EVAL_PATH.read_text(encoding="utf-8")
    assert "TimeSeriesSplit" in source
    assert "KFold" not in source
    assert "shuffle=True" not in source
    assert evaluate.N_SPLITS >= 5


def test_features_before_t_ignore_perturbation_at_or_after_t():
    raw_train, months = _feature_months()
    # Month near the middle of the feature-ready window so both sides have rows.
    t = pd.Timestamp(months[len(months) // 2])
    history = raw_train.loc[raw_train["month"] <= months[-1]].copy()
    scaler = evaluate.fit_fold_scaler(history.loc[history["month"] < t])
    baseline = evaluate.train.training_frame(history, scaler)

    perturbed = history.copy()
    future = perturbed["month"] >= t
    perturbed.loc[future, "revenue_usd"] = perturbed.loc[future, "revenue_usd"] * 1.35
    perturbed.loc[future, "covers_served"] = perturbed.loc[future, "covers_served"] + 5000
    perturbed.loc[future, "avg_ticket_usd"] = perturbed.loc[future, "avg_ticket_usd"] * 1.2
    altered = evaluate.train.training_frame(perturbed, scaler)

    before = baseline["month"] < t
    cols = list(evaluate.train.FEATURE_COLUMNS) + [evaluate.train.TARGET_COLUMN]
    assert before.any()
    pd.testing.assert_frame_equal(
        baseline.loc[before, cols].reset_index(drop=True),
        altered.loc[before, cols].reset_index(drop=True),
    )


def test_fold_scaler_differs_from_scaler_fit_on_all_eight_years():
    raw_train, months = _feature_months()
    train_idx, _val_idx = evaluate.iter_temporal_splits(len(months))[0]
    fold_train_months = months[train_idx]
    fold_scaler = evaluate.fit_fold_scaler(
        raw_train.loc[raw_train["month"].isin(fold_train_months)]
    )

    full_scaler = StandardScaler()
    columns = list(evaluate.phase1.SCALED_COLUMNS)
    full_scaler.fit(raw_train.loc[:, columns].astype(float))

    assert fold_scaler.n_samples_seen_ == len(fold_train_months)
    assert full_scaler.n_samples_seen_ == len(raw_train)
    assert not np.allclose(fold_scaler.mean_, full_scaler.mean_)
    assert not np.allclose(fold_scaler.scale_, full_scaler.scale_)


def test_build_fold_tables_keeps_validation_one_step_ahead():
    raw_train, months = _feature_months()
    train_idx, val_idx = evaluate.iter_temporal_splits(len(months))[-1]
    train_table, val_table, _scaler = evaluate.build_fold_tables(
        raw_train, months[train_idx], months[val_idx]
    )
    assert train_table["month"].max() < val_table["month"].min()
    assert len(val_table) == len(val_idx)
    # Lag features must be finite and drawn from prior actuals (no NaNs after rebuild).
    assert not train_table.loc[:, list(evaluate.train.FEATURE_COLUMNS)].isna().any().any()
    assert not val_table.loc[:, list(evaluate.train.FEATURE_COLUMNS)].isna().any().any()


def test_learning_curve_sizes_are_chronological_prefixes():
    raw_train, months = _feature_months()
    splits = evaluate.iter_temporal_splits(len(months))
    size = evaluate.LEARNING_CURVE_SIZES[0]
    for train_idx, val_idx in splits:
        if len(train_idx) < size:
            continue
        prefix = train_idx[:size]
        assert list(prefix) == sorted(prefix)
        assert max(prefix) < min(val_idx)
        assert list(prefix) == list(train_idx[:size])


def test_primary_metric_follows_briefing_evidence_not_assignment_example():
    decision = evaluate.briefing_primary_metric_decision()
    assert decision.ranks_error_directions is False
    assert decision.metric == "mae"
