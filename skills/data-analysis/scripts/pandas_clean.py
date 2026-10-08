"""
Safe snippet for basic pandas cleaning. Copy and adapt for your dataset.
Run: python pandas_clean.py  (ensure pandas is installed)
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_CSV_PATH = Path("data.csv")


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def load_csv(path: Path):
    """Load a CSV with scoped I/O and parse error handling."""
    try:
        import pandas as pd
    except ImportError:
        fail("pandas is required. Install it with: pip install pandas")

    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        fail(f"Input file not found: {path}")
    except PermissionError:
        fail(f"Permission denied reading input file: {path.name}")
    except IsADirectoryError:
        fail(f"Expected a CSV file but found a directory: {path.name}")
    except UnicodeDecodeError:
        fail(f"Could not decode CSV as text: {path.name}")
    except pd.errors.EmptyDataError:
        fail(f"CSV file is empty: {path.name}")
    except pd.errors.ParserError:
        fail(f"CSV file is malformed and could not be parsed: {path.name}")
    except OSError:
        fail(f"Could not read input file: {path.name}")


def clean_dataframe(df):
    """Apply the existing cleaning steps. Rejects empty frames as critical failures."""
    if df is None or getattr(df, "empty", True):
        fail("CSV loaded successfully but contains no data rows to clean.")

    print("df_shape", df.shape)
    print("df_dtypes", df.dtypes)

    # Drop fully null columns
    df = df.dropna(axis=1, how="all")
    print("df_shape_after_drop_all_null_cols", df.shape)

    if df.empty or df.shape[1] == 0:
        fail(
            "After dropping fully null columns, no usable columns remain. "
            "Cleaning aborted."
        )

    # Fill or drop nulls in key columns (customise columns)
    # df = df.dropna(subset=["required_col"])
    # df["optional_col"] = df["optional_col"].fillna(0)

    # Normalise column names (optional)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    print("df_columns", list(df.columns))

    # Deduplicate (optional)
    before = len(df)
    df = df.drop_duplicates()
    print("rows_dropped_duplicates", before - len(df))

    if df.empty:
        fail("After deduplication, no data rows remain. Cleaning aborted.")

    # Sample output
    print("df_head", df.head())
    return df


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = Path(args[0]) if args else DEFAULT_CSV_PATH

    df = load_csv(path)
    clean_dataframe(df)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        print(
            "Unexpected error while cleaning CSV. Check the input file and try again.",
            file=sys.stderr,
        )
        sys.exit(1)
