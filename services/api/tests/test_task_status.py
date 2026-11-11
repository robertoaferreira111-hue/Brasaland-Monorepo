"""GET /tasks/{task_id} maps Celery states without a live broker."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.deps import current_user_email
from app.main import app
from app.routers.tasks import task_status_body

client = TestClient(app)


def setup_function() -> None:
    app.dependency_overrides[current_user_email] = lambda: "staff@example.com"


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_task_status_requires_a_staff_token() -> None:
    app.dependency_overrides.clear()
    response = client.get("/tasks/missing-task")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_status_mapping_covers_each_public_state() -> None:
    task_id = "task-1"
    assert task_status_body(task_id, "PENDING", None) == {
        "task_id": task_id,
        "status": "pending",
        "result": None,
    }
    assert task_status_body(task_id, "STARTED", None)["status"] == "started"
    assert task_status_body(task_id, "RETRY", None)["status"] == "started"
    assert task_status_body(task_id, "SUCCESS", {"run_id": "run-1", "status": "success"}) == {
        "task_id": task_id,
        "status": "success",
        "result": {"run_id": "run-1", "status": "success"},
    }
    assert task_status_body(task_id, "FAILURE", RuntimeError("boom")) == {
        "task_id": task_id,
        "status": "failure",
        "result": "boom",
    }
    assert task_status_body(task_id, "REVOKED", None) == {
        "task_id": task_id,
        "status": "failure",
        "result": "task failed",
    }
    unknown = task_status_body(task_id, "CUSTOM", "raw")
    assert unknown["status"] == "pending"
    assert unknown["result"] is None
    assert "CUSTOM" not in str(unknown)


def test_unknown_task_id_is_pending(monkeypatch) -> None:
    monkeypatch.setattr("app.routers.tasks.load_task_view", lambda task_id: ("PENDING", None))
    response = client.get("/tasks/does-not-exist")
    assert response.status_code == 200
    assert response.json() == {
        "task_id": "does-not-exist",
        "status": "pending",
        "result": None,
    }
