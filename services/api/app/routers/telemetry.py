"""POST /telemetry/events. Per-event validation, one bulk insert."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, ValidationError

from app.telemetry_event import TelemetryEvent
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
    accepted: list[dict[str, Any]] = []
    rejected = 0
    for raw in body.events:
        try:
            event = TelemetryEvent.model_validate(raw)
        except ValidationError:
            rejected += 1
            continue
        accepted.append(event.model_dump(mode="json"))
    if accepted:
        store.insert_batch(accepted)
    return TelemetryIngestResult(
        received=len(body.events),
        stored=len(accepted),
        rejected=rejected,
    )
