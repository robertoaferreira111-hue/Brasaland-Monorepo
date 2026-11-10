"""GET /tasks/{task_id} for the Celery weekly pipeline task."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.deps import current_user_email

router = APIRouter(tags=["tasks"])

_STATUS = {
    "PENDING": "pending",
    "STARTED": "started",
    "RETRY": "started",
    "SUCCESS": "success",
    "FAILURE": "failure",
    "REVOKED": "failure",
}


def load_task_view(task_id: str) -> tuple[str, object]:
    from celery.result import AsyncResult

    from app.celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)
    return str(result.state), result.result


def task_status_body(task_id: str, state: str, raw_result: object) -> dict[str, Any]:
    """Map a Celery state onto the public vocabulary. Unknown states stay pending."""
    status_name = _STATUS.get(state, "pending")
    if status_name == "success":
        payload: object = raw_result
    elif status_name == "failure":
        text = "" if raw_result is None else str(raw_result).strip()
        payload = text or "task failed"
    else:
        payload = None
    return {"task_id": task_id, "status": status_name, "result": payload}


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str, _email: str = Depends(current_user_email)) -> dict[str, Any]:
    state, raw_result = load_task_view(task_id)
    return task_status_body(task_id, state, raw_result)
