"""Bulk insert of telemetry_events rows through the Supabase REST API.

One POST to /rest/v1/telemetry_events sends the accepted rows. The primary key
is the producer event id. `resolution=ignore-duplicates` keeps a second
delivery of that id from inserting another row. The service-role key stays on
the server.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.errors import StorageError

_TABLE = "telemetry_events"


class TelemetryBatchStore:
    """One call inserts the whole accepted batch. There is no per-event insert."""

    def insert_batch(self, rows: list[dict[str, Any]]) -> int:
        del rows
        raise StorageError("Storage unavailable")


class SupabaseTelemetryStore(TelemetryBatchStore):
    def __init__(
        self,
        url: str,
        service_role_key: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._key = service_role_key
        self._client = client

    def insert_batch(self, rows: list[dict[str, Any]]) -> int:
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=30.0)
        try:
            try:
                response = client.post(
                    f"{self._url}/rest/v1/{_TABLE}",
                    params={"on_conflict": "id"},
                    headers={
                        "apikey": self._key,
                        "Authorization": f"Bearer {self._key}",
                        "Content-Type": "application/json",
                        "Prefer": "resolution=ignore-duplicates,return=representation",
                    },
                    json=rows,
                )
            except httpx.HTTPError as exc:
                raise StorageError("Storage unavailable") from exc
        finally:
            if owns_client:
                client.close()
        if response.status_code >= 400:
            raise StorageError("Storage unavailable")
        try:
            data = response.json()
        except ValueError as exc:
            raise StorageError("Storage unavailable") from exc
        if not isinstance(data, list):
            raise StorageError("Storage unavailable")
        return len(data)


def get_telemetry_store() -> TelemetryBatchStore:
    settings = get_settings()
    url = settings.supabase_url
    key = settings.supabase_service_role_key
    if not url or not key:
        return TelemetryBatchStore()
    return SupabaseTelemetryStore(url, key)
