import os
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-key")


@pytest.fixture()
def auth_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "auth.json"
    monkeypatch.setattr("app.database.DEFAULT_DB_PATH", db_path)
    return db_path
