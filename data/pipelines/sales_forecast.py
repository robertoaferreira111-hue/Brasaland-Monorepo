"""Prepare Brasaland monthly sales for a later forecast model.

Nulls are rejected, not imputed. An empty required cell, a non-positive
``revenue_usd``, or a gap in the monthly series raises. The provided CSV
has no empty cells. Filling a missing month would invent a point inside
the January drop or the December peak described in ``CONTEXT-company.md``.

``RANDOM_SEED`` is the single seed for later training phases. It is the
seed named in ``CONTEXT-company.md`` (``random_state=42``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.preprocessing import StandardScaler

RANDOM_SEED = 42

REQUIRED_COLUMNS = (
    "month",
    "revenue_usd",
    "covers_served",
    "avg_ticket_usd",
    "market",
)

SCALED_COLUMNS = ("covers_served", "avg_ticket_usd")

TRAIN_YEARS = 8


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_csv_path() -> Path:
    return repo_root() / "data" / "raw" / "brasaland_sales.csv"


def load_sales(csv_path: Path | None = None) -> pd.DataFrame:
    """Load the provided CSV and keep consolidated rows in month order."""
    path = csv_path or default_csv_path()
    frame = pd.read_csv(path)
    missing = [name for name in REQUIRED_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError(f"CSV is missing columns {missing}")

    frame = frame.loc[:, list(REQUIRED_COLUMNS)].copy()
    _reject_empty_cells(frame)
    frame["month"] = pd.to_datetime(frame["month"])
    frame["revenue_usd"] = pd.to_numeric(frame["revenue_usd"])
    frame["covers_served"] = pd.to_numeric(frame["covers_served"])
    frame["avg_ticket_usd"] = pd.to_numeric(frame["avg_ticket_usd"])
    if frame[["revenue_usd", "covers_served", "avg_ticket_usd"]].isna().any().any():
        raise ValueError("Required numeric cell is empty; refusing to impute")
    if (frame["revenue_usd"] <= 0).any():
        raise ValueError("revenue_usd must be positive")

    consolidated = frame.loc[frame["market"].astype(str).str.strip() == "consolidated"].copy()
    if consolidated.empty:
        raise ValueError("No consolidated rows")
    consolidated = consolidated.sort_values("month").reset_index(drop=True)
    _require_continuous_months(consolidated["month"])
    return consolidated


def _reject_empty_cells(frame: pd.DataFrame) -> None:
    empty = frame.isna()
    for name in REQUIRED_COLUMNS:
        if frame[name].dtype == object:
            empty[name] = empty[name] | frame[name].astype(str).str.strip().eq("")
    if bool(empty.to_numpy().any()):
        raise ValueError("Required cell is empty; refusing to impute")


def _require_continuous_months(months: pd.Series) -> None:
    expected = pd.date_range(months.iloc[0], months.iloc[-1], freq="MS")
    actual = pd.DatetimeIndex(months)
    if len(actual) != len(expected) or not actual.equals(expected):
        raise ValueError("Monthly series has a gap or a duplicate")


def split_chronological(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """First 8 years train, the following months test. Boundary comes from the dates."""
    start = frame["month"].min()
    boundary = start + pd.DateOffset(years=TRAIN_YEARS)
    train = frame.loc[frame["month"] < boundary].reset_index(drop=True)
    test = frame.loc[frame["month"] >= boundary].reset_index(drop=True)
    if train.empty or test.empty:
        raise ValueError("Chronological split produced an empty side")
    return train, test


@dataclass(frozen=True)
class PreparedSales:
    train: pd.DataFrame
    test: pd.DataFrame
    scaler: StandardScaler
    scaled_columns: tuple[str, ...]


def scale_features(train: pd.DataFrame, test: pd.DataFrame) -> PreparedSales:
    """Scale guest-count and ticket columns. Fit on training rows only.

    ``revenue_usd`` stays in USD so a later squared error remains in USD squared.
    ``StandardScaler`` has no seed; ``RANDOM_SEED`` is reserved for model fitting.
    """
    scaler = StandardScaler()
    columns = list(SCALED_COLUMNS)
    train_out = train.copy()
    test_out = test.copy()
    train_out[columns] = train_out[columns].astype(float)
    test_out[columns] = test_out[columns].astype(float)
    scaler.fit(train_out.loc[:, columns])
    train_out.loc[:, columns] = scaler.transform(train_out.loc[:, columns])
    test_out.loc[:, columns] = scaler.transform(test_out.loc[:, columns])
    return PreparedSales(
        train=train_out,
        test=test_out,
        scaler=scaler,
        scaled_columns=SCALED_COLUMNS,
    )


def prepare(csv_path: Path | None = None) -> PreparedSales:
    frame = load_sales(csv_path)
    train, test = split_chronological(frame)
    return scale_features(train, test)
