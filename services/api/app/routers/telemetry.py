"""Persist accepted telemetry events from one batch envelope."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, ValidationError

from app.models import TelemetryBatchResponse, TelemetryEvent
from app.telemetry_config import TELEMETRY_PATH, TELEMETRY_SERVICE
from app.telemetry_schema import TelemetrySchemaError, validate_event
from app.telemetry_store import (
    TelemetryStore,
    TelemetryStoreError,
    event_row,
    get_telemetry_store,
)

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["telemetry"])


class TelemetryEnvelope(BaseModel):
    """Batch envelope. Items stay raw so one invalid event does not reject the list."""

    model_config = ConfigDict(extra="forbid")

    events: list[Any]


def _partition(events: list[Any]) -> tuple[list[TelemetryEvent], int]:
    accepted: list[TelemetryEvent] = []
    rejected = 0
    for raw in events:
        if not isinstance(raw, dict):
            rejected += 1
            continue
        try:
            event = TelemetryEvent.model_validate(raw)
            validate_event(event.model_dump(mode="json"))
        except (ValidationError, TelemetrySchemaError):
            rejected += 1
            continue
        accepted.append(event)
    return accepted, rejected


@router.post(
    TELEMETRY_PATH,
    response_model=TelemetryBatchResponse,
    status_code=status.HTTP_200_OK,
)
def receive_events(
    envelope: TelemetryEnvelope,
    store: Annotated[TelemetryStore, Depends(get_telemetry_store)],
) -> TelemetryBatchResponse:
    accepted, rejected = _partition(envelope.events)
    received = len(envelope.events)
    if not accepted:
        return TelemetryBatchResponse(received=received, stored=0, rejected=rejected)
    try:
        store.insert_many(
            [event_row(event, TELEMETRY_SERVICE) for event in accepted]
        )
    except TelemetryStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telemetry events were not stored",
        ) from exc
    stored = len(accepted)
    logger.info(
        "telemetry events received=%s stored=%s rejected=%s event_types=%s",
        received,
        stored,
        rejected,
        ",".join(event.event_type for event in accepted),
    )
    return TelemetryBatchResponse(
        received=received,
        stored=stored,
        rejected=rejected,
    )
