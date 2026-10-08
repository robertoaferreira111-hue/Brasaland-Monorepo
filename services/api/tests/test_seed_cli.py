"""CLI exit codes and stderr diagnostics for the seed script."""

from __future__ import annotations

import pytest

from app.errors import StorageError
from app.seed import main, seed_suppliers


def test_main_success_prints_to_stdout(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "suppliers.json"
    monkeypatch.setattr(
        "app.seed.seed_suppliers",
        lambda: seed_suppliers(db_path),
    )

    code = main([])
    captured = capsys.readouterr()
    assert code == 0
    assert "Seed complete" in captured.out
    assert captured.err == ""


def test_main_storage_failure_exits_nonzero_on_stderr(monkeypatch, capsys):
    def boom():
        raise StorageError("Storage unavailable")

    monkeypatch.setattr("app.seed.seed_suppliers", boom)
    code = main([])
    captured = capsys.readouterr()
    assert code == 1
    assert "Seed failed" in captured.err
    assert "Seed complete" not in captured.out
    assert "/Users/" not in captured.err
    assert "Traceback" not in captured.err


def test_main_reports_partial_insert_failure(monkeypatch, capsys):
    def boom():
        raise ValueError(
            "could not write the supplier database after inserting 2 of 5 "
            "pending row(s). Fix storage and re-run seed; existing names are skipped."
        )

    monkeypatch.setattr("app.seed.seed_suppliers", boom)
    code = main([])
    captured = capsys.readouterr()
    assert code == 1
    assert "after inserting 2 of 5" in captured.err
    assert "Seed complete" not in captured.out


def test_seed_suppliers_storage_error_on_open(tmp_path, monkeypatch):
    def boom(_path=None):
        raise StorageError("Storage unavailable")

    monkeypatch.setattr("app.seed.open_db", boom)
    with pytest.raises(StorageError):
        seed_suppliers(tmp_path / "suppliers.json")
