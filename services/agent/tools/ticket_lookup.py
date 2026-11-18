"""Read one incident, or a filtered list, from the incident service.

Transport is in-process. ``app.incidents`` imports the TinyDB helpers, the
domain models, and password helpers. It does not import ``app.main``,
``app.celery_app``, or ``app.config``, and it does not require ``REDIS_URL``.
The HTTP routes are not called. Staff bearer auth stays on those routes;
this reader uses the same functions the routes call after auth.

``BRASALAND_ROOT`` changes only the CSV path used by ``seed_incidents`` and
``read_incident_csv``: ``$BRASALAND_ROOT/data/raw/incidents-brasaland.csv``.
``get_incident``, ``list_incidents``, and ``get_incident_record`` read the
TinyDB file next to the API package and ignore that variable. Importing the
incident functions does not read it either. When ``app`` is not already
importable, this module adds ``services/api`` from its own file path, not
from ``BRASALAND_ROOT``.

Ids in the incident file are ``BRS-`` plus six digits, ``BRS-000001`` through
``BRS-000100``. A bare number is that format: ``1`` and ``"1"`` become
``BRS-000001``. ``BRS-000001`` and ``brs-000001`` stay that id. A value that
cannot be padded into six digits, including a sentence such as
``ticket 482``, is not an id. This function does not parse a question.

Null CSV fields are returned as ``not recorded``. Status, date, id, and
reporter id are required on a stored row and are returned as stored. A
missing id is ``not_found``. Timeout, a storage failure, and an invalid
filter are ``timeout`` or ``http_error``. The function does not raise for
those outcomes and does not fill in a status or category.

``INCIDENT_LOOKUP_TIMEOUT_SECONDS`` sets the bound. Unset means 5. A value
outside 3–5 seconds is ``http_error`` and does not read storage. The bound
is a thread join: the caller returns when the join expires even if TinyDB
is still in the worker thread.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import re
import sys
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

NOT_RECORDED = "not recorded"
TIMEOUT = "timeout"
NOT_FOUND = "not_found"
HTTP_ERROR = "http_error"

TIMEOUT_ENV = "INCIDENT_LOOKUP_TIMEOUT_SECONDS"
DEFAULT_TIMEOUT_SECONDS = 5.0
MIN_TIMEOUT_SECONDS = 3.0
MAX_TIMEOUT_SECONDS = 5.0

LookupErrorCode = Literal["timeout", "not_found", "http_error"]

_BARE_ID = re.compile(r"^(?:BRS-)?(\d{1,6})$", re.IGNORECASE)


class TicketLookupInput(BaseModel):
    """Id and the list filters the incident API accepts."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str | int | None = None
    status: str | None = None
    category: str | None = None


class IncidentFields(BaseModel):
    """One incident as the read API stores it. Nulls are already replaced."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str
    date: str
    location_id: str
    category: str
    description: str
    status: str
    customer_id: str
    satisfaction_score: int | str
    reporter_id: str


class TicketLookupOutput(BaseModel):
    """found is true only when at least one stored row matched."""

    model_config = ConfigDict(extra="forbid")

    found: bool
    incidents: list[IncidentFields] = Field(default_factory=list)
    error: LookupErrorCode | None = None


def normalize_incident_id(value: str | int) -> str | None:
    """Return ``BRS-######`` or None when the value is not that id shape."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        if value < 0 or value > 999_999:
            return None
        return f"BRS-{value:06d}"
    match = _BARE_ID.fullmatch(value.strip())
    if match is None:
        return None
    return f"BRS-{int(match.group(1)):06d}"


def resolve_lookup_timeout(explicit: float | None = None) -> float:
    """Seconds for this call. The allowed window is 3 through 5 inclusive."""
    if explicit is None:
        raw = os.environ.get(TIMEOUT_ENV, "").strip()
        if not raw:
            return DEFAULT_TIMEOUT_SECONDS
        value: object = float(raw)
    else:
        value = explicit
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Incident lookup timeout must be a number of seconds.")
    seconds = float(value)
    if seconds < MIN_TIMEOUT_SECONDS or seconds > MAX_TIMEOUT_SECONDS:
        raise ValueError("Incident lookup timeout must be from 3 to 5 seconds.")
    return seconds


def lookup_ticket(
    incident_id: str | int | None = None,
    *,
    status: str | None = None,
    category: str | None = None,
    timeout_seconds: float | None = None,
) -> TicketLookupOutput:
    """Read incidents. An id limits the read to that row; filters apply either way."""
    try:
        timeout = resolve_lookup_timeout(timeout_seconds)
    except (TypeError, ValueError):
        return _failed(HTTP_ERROR)
    normalized = _normalize_query_id(incident_id)
    if incident_id is not None and normalized is None:
        return _failed(NOT_FOUND)
    try:
        if not _filters_allowed(status, category):
            return _failed(HTTP_ERROR)
    except Exception:
        logger.exception("Incident lookup could not validate filters")
        return _failed(HTTP_ERROR)

    try:
        records = _call_with_timeout(
            lambda: _load_records(normalized, status, category),
            timeout,
        )
    except TimeoutError:
        return _failed(TIMEOUT)
    except Exception:
        logger.exception("Incident lookup failed")
        return _failed(HTTP_ERROR)
    if not records:
        return _failed(NOT_FOUND)
    return TicketLookupOutput(
        found=True,
        incidents=[_snapshot(record) for record in records],
        error=None,
    )


def _normalize_query_id(incident_id: str | int | None) -> str | None:
    if incident_id is None:
        return None
    return normalize_incident_id(incident_id)


def _filters_allowed(status: str | None, category: str | None) -> bool:
    from typing import get_args

    _ensure_api_importable()
    from app.incidents import IncidentCategory, IncidentStatus

    if status is not None and status not in get_args(IncidentStatus):
        return False
    if category is not None and category not in get_args(IncidentCategory):
        return False
    return True


def _failed(code: LookupErrorCode) -> TicketLookupOutput:
    return TicketLookupOutput(found=False, incidents=[], error=code)


def _text(value: str | None) -> str:
    if value is None:
        return NOT_RECORDED
    return value


def _snapshot(record: object) -> IncidentFields:
    date = getattr(record, "date")
    score = getattr(record, "satisfaction_score")
    return IncidentFields(
        incident_id=getattr(record, "incident_id"),
        date=date.isoformat(),
        location_id=_text(getattr(record, "location_id")),
        category=_text(getattr(record, "category")),
        description=_text(getattr(record, "description")),
        status=getattr(record, "status"),
        customer_id=_text(getattr(record, "customer_id")),
        satisfaction_score=NOT_RECORDED if score is None else score,
        reporter_id=getattr(record, "reporter_id"),
    )


def _ensure_api_importable() -> None:
    if importlib.util.find_spec("app.incidents") is not None:
        return
    api_root = Path(__file__).resolve().parents[3] / "services" / "api"
    entry = str(api_root)
    if entry not in sys.path:
        sys.path.insert(0, entry)
    importlib.invalidate_caches()
    if importlib.util.find_spec("app.incidents") is None:
        raise ImportError("app.incidents is not importable from the agent service")


def _load_records(
    incident_id: str | None,
    status: str | None,
    category: str | None,
) -> list:
    """Read through get_incident or list_incidents. No insert and no HTTP route."""
    _ensure_api_importable()
    from app.database import get_incidents_table
    from app.incidents import get_incident, list_incidents

    table_iter = get_incidents_table()
    table = next(table_iter)
    try:
        if incident_id is not None:
            record = get_incident(table, incident_id)
            if record is None:
                return []
            if status is not None and record.status != status:
                return []
            if category is not None and record.category != category:
                return []
            return [record]
        return list_incidents(table, status=status, category=category)
    finally:
        table_iter.close()


def _call_with_timeout(fn, timeout: float):
    box: dict[str, object] = {}

    def target() -> None:
        try:
            box["value"] = fn()
        except Exception as exc:
            box["error"] = exc

    worker = threading.Thread(target=target, name="incident-ticket-lookup", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise TimeoutError
    error = box.get("error")
    if isinstance(error, Exception):
        raise error
    if "value" not in box:
        raise RuntimeError("Incident lookup ended without a result")
    return box["value"]
