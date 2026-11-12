"""Chronological split and train-only scaling for Brasaland sales."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
_MODULE = _ROOT / "data" / "pipelines" / "sales_forecast.py"
_SPEC = importlib.util.spec_from_file_location("brasaland_sales_forecast_pipeline", _MODULE)
assert _SPEC is not None and _SPEC.loader is not None
sales = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = sales
_SPEC.loader.exec_module(sales)


def _unscaled_split():
    frame = sales.load_sales()
    return sales.split_chronological(frame)


def test_train_and_test_periods_do_not_overlap():
    train, test = _unscaled_split()
    assert set(train["month"]).isdisjoint(set(test["month"]))


def test_train_ends_before_test_begins():
    train, test = _unscaled_split()
    assert train["month"].max() < test["month"].min()


def test_train_spans_eight_years_and_test_spans_two():
    train, test = _unscaled_split()
    assert train["month"].max() == train["month"].min() + pd.DateOffset(years=8) - pd.DateOffset(months=1)
    assert test["month"].max() == test["month"].min() + pd.DateOffset(years=2) - pd.DateOffset(months=1)


def test_scaler_is_fit_on_training_rows_only():
    train, test = _unscaled_split()
    prepared = sales.scale_features(train, test)
    columns = list(sales.SCALED_COLUMNS)
    train_mean = train.loc[:, columns].mean().to_numpy()
    combined_mean = pd.concat([train, test], ignore_index=True).loc[:, columns].mean().to_numpy()

    assert prepared.scaler.n_samples_seen_ == len(train)
    assert np.allclose(prepared.scaler.mean_, train_mean)
    assert not np.allclose(prepared.scaler.mean_, combined_mean)
