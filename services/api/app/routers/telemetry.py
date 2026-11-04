"""POST /telemetry/events. Per-event validation, one bulk insert."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, ValidationError

from app.telemetry_event import TelemetryEvent
from app.telemetry_mapping import map_event_to_row
from app.telemetry_store import TelemetryBatchStore, get_telemetry_store

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class TelemetryEnvelope(BaseModel):
    """Batch envelope. `events` is not typed as `list[TelemetryEvent]`."""

    model_config = ConfigDict(extra="forbid")

    events: list[Any]


class TelemetryIngestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    received: int
    stored: int
    rejected: int


@router.post("/events", status_code=status.HTTP_200_OK)
def ingest_events(
    body: TelemetryEnvelope,
    store: Annotated[TelemetryBatchStore, Depends(get_telemetry_store)],
) -> TelemetryIngestResult:
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    rejected = 0
    for raw in body.events:
        try:
            event = TelemetryEvent.model_validate(raw)
        except ValidationError:
            rejected += 1
            continue
        row = map_event_to_row(event)
        if row["id"] in seen_ids:
            continue
        seen_ids.add(row["id"])
        rows.append(row)
    stored = store.insert_batch(rows) if rows else 0
    return TelemetryIngestResult(
        received=len(body.events),
        stored=stored,
        rejected=rejected,
    )
