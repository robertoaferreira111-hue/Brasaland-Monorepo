import os
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-auth-suite-32b")


@pytest.fixture()
def auth_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "auth.json"
    monkeypatch.setattr("app.database.DEFAULT_DB_PATH", db_path)
    return db_path


@pytest.fixture()
def client(auth_db_path: Path):
    """HTTP client bound to this test's empty auth database."""
    from fastapi.testclient import TestClient

    from app.main import app

    del auth_db_path
    with TestClient(app) as test_client:
        yield test_client
