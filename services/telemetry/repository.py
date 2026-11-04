"""Supabase REST reads for `telemetry_events` with SQL-side filters.

Reuses the same server-side env vars as capture (`SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`). Does not write rows.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = Path(__file__).resolve().parents[1] / "api"

# Columns needed by Phase 1 metrics (never SELECT *).
METRIC_COLUMNS = ("id", "timestamp", "event_type", "level", "tags")


class TelemetryRepositoryError(RuntimeError):
    """Raised when Supabase cannot satisfy a telemetry read."""


def _load_env_files() -> None:
    for path in (
        REPO_ROOT / ".env" / "local",
        REPO_ROOT / ".env",
        API_ROOT / ".env",
    ):
        if path.is_file():
            load_dotenv(path, override=False)


def _supabase_config() -> tuple[str, str]:
    _load_env_files()
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key:
        raise TelemetryRepositoryError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for reads"
        )
    return url, key


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise TelemetryRepositoryError("start_date/end_date must be timezone-aware UTC")
    return value.isoformat().replace("+00:00", "Z")


def fetch_events(
    *,
    start_date: datetime,
    end_date: datetime,
    event_types: Sequence[str] | None = None,
    columns: Sequence[str] = METRIC_COLUMNS,
) -> list[dict[str, Any]]:
    """Load filtered rows: timestamp >= start AND timestamp < end (UTC).

    Event-type filtering uses PostgREST `in.()` when `event_types` is set.
    """
    # Validate tz before comparing / formatting.
    start_iso = _iso(start_date)
    end_iso = _iso(end_date)
    if start_date >= end_date:
        return []

    url, key = _supabase_config()
    select = ",".join(columns)
    params: list[tuple[str, str]] = [
        ("select", select),
        ("timestamp", f"gte.{start_iso}"),
        ("timestamp", f"lt.{end_iso}"),
        ("order", "timestamp.asc"),
    ]
    if event_types:
        joined = ",".join(event_types)
        params.append(("event_type", f"in.({joined})"))

    endpoint = f"{url}/rest/v1/telemetry_events"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(endpoint, headers=headers, params=params)
    except httpx.HTTPError as exc:
        raise TelemetryRepositoryError("telemetry read transport failure") from exc

    if response.status_code >= 400:
        raise TelemetryRepositoryError(
            f"telemetry read failed with status {response.status_code}"
        )
    payload = response.json()
    if not isinstance(payload, list):
        raise TelemetryRepositoryError("telemetry read returned a non-list payload")
    return payload
