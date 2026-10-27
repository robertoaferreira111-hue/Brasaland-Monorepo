"""Acknowledge telemetry batches. This route does not store events."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.models import TelemetryBatch, TelemetryBatchResponse
from app.telemetry_config import TELEMETRY_PATH
from app.telemetry_schema import TelemetrySchemaError, validate_event

logger = logging.getLogger("uvicorn.error")

router = APIRouter(tags=["telemetry"])


@router.post(
    TELEMETRY_PATH,
    response_model=TelemetryBatchResponse,
    status_code=status.HTTP_200_OK,
)
def receive_events(batch: TelemetryBatch) -> TelemetryBatchResponse:
    for index, event in enumerate(batch.events):
        try:
            validate_event(event.model_dump(mode="json"))
        except TelemetrySchemaError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"events[{index}]: {exc}",
            ) from exc
    logger.info(
        "telemetry events received count=%s event_types=%s",
        len(batch.events),
        ",".join(event.event_type for event in batch.events),
    )
    return TelemetryBatchResponse(received=len(batch.events))
