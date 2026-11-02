"""Bulk insert port for accepted telemetry events.

This service has no Supabase client and no telemetry_events table. The default
store therefore fails the batch. It does not report those events as stored.
"""

from __future__ import annotations

from typing import Any

from app.errors import StorageError


class TelemetryBatchStore:
    """One call inserts the whole accepted batch. There is no per-event insert."""

    def insert_batch(self, events: list[dict[str, Any]]) -> None:
        del events
        raise StorageError("Storage unavailable")


def get_telemetry_store() -> TelemetryBatchStore:
    return TelemetryBatchStore()
