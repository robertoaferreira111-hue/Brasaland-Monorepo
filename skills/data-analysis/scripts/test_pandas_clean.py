"""Exit codes and stderr diagnostics for pandas_clean.py."""

from __future__ import annotations

import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent / "pandas_clean.py"


def _run_script(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )


class PandasCleanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import pandas  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("pandas is not installed") from None

    def test_success_preserves_stdout_metrics(self) -> None:
        from pandas_clean import clean_dataframe, load_csv

        import pandas as pd

        csv_path = Path(self.id().replace(".", "_") + "_ok.csv")
        self.addCleanup(lambda: csv_path.exists() and csv_path.unlink())
        pd.DataFrame({"Name": ["A", "A", "B"], "Value": [1, 1, 2]}).to_csv(
            csv_path, index=False
        )

        buffer = io.StringIO()
        with mock.patch("sys.stdout", buffer):
            df = load_csv(csv_path)
            cleaned = clean_dataframe(df)
        output = buffer.getvalue()
        self.assertIn("df_shape", output)
        self.assertIn("df_columns", output)
        self.assertIn("rows_dropped_duplicates", output)
        self.assertIn("df_head", output)
        self.assertEqual(len(cleaned), 2)

    def test_missing_file_exits_one_on_stderr(self) -> None:
        result = _run_script("missing-data.csv", cwd=SCRIPT.parent)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Input file not found", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)

    def test_empty_csv_exits_one(self) -> None:
        empty = SCRIPT.parent / "empty_input.csv"
        empty.write_text("", encoding="utf-8")
        self.addCleanup(lambda: empty.exists() and empty.unlink())
        result = _run_script(str(empty), cwd=SCRIPT.parent)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            "empty" in result.stderr.lower() or "no data" in result.stderr.lower()
        )
        self.assertNotIn("df_shape", result.stdout)

    def test_header_only_csv_exits_one(self) -> None:
        header_only = SCRIPT.parent / "header_only.csv"
        header_only.write_text("name,value\n", encoding="utf-8")
        self.addCleanup(lambda: header_only.exists() and header_only.unlink())
        result = _run_script(str(header_only), cwd=SCRIPT.parent)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no data rows", result.stderr.lower())

    def test_malformed_csv_exits_one(self) -> None:
        bad = SCRIPT.parent / "bad.csv"
        # Unclosed quote commonly triggers a parser error.
        bad.write_text('name,value\n"broken,1\n', encoding="utf-8")
        self.addCleanup(lambda: bad.exists() and bad.unlink())
        result = _run_script(str(bad), cwd=SCRIPT.parent)
        self.assertEqual(result.returncode, 1)
        self.assertIn("malformed", result.stderr.lower())
        self.assertNotIn("Traceback", result.stderr)

    def test_success_via_cli(self) -> None:
        import pandas as pd

        good = SCRIPT.parent / "good_input.csv"
        pd.DataFrame({"City Name": ["Medellin"], "Score": [10]}).to_csv(
            good, index=False
        )
        self.addCleanup(lambda: good.exists() and good.unlink())
        result = _run_script(str(good), cwd=SCRIPT.parent)
        self.assertEqual(result.returncode, 0)
        self.assertIn("df_shape", result.stdout)
        self.assertIn("city_name", result.stdout)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
