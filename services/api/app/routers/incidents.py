"""Read-only incident routes. Writes are not registered."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from tinydb.table import Table

from app.database import get_incidents_table
from app.deps import current_user_email
from app.errors import (
    STORAGE_UNAVAILABLE,
    STORED_INCIDENT_INVALID,
    DataIntegrityError,
    StorageError,
)
from app.incidents import (
    IncidentCategory,
    IncidentRecord,
    IncidentStatus,
    get_incident,
    list_incidents,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/incidents",
    tags=["incidents"],
    dependencies=[Depends(current_user_email)],
)


def _missing() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Incident not found",
    )


def _storage_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=STORAGE_UNAVAILABLE,
    )


def _stored_invalid() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=STORED_INCIDENT_INVALID,
    )


def incidents_dependency() -> Iterator[Table]:
    try:
        yield from get_incidents_table()
    except StorageError as exc:
        raise _storage_unavailable() from exc


@router.get("", response_model=list[IncidentRecord])
def list_incident_records(
    table: Annotated[Table, Depends(incidents_dependency)],
    status_filter: Annotated[IncidentStatus | None, Query(alias="status")] = None,
    category: Annotated[IncidentCategory | None, Query()] = None,
) -> list[IncidentRecord]:
    try:
        return list_incidents(table, status=status_filter, category=category)
    except StorageError as exc:
        raise _storage_unavailable() from exc
    except DataIntegrityError as exc:
        logger.warning("Stored incident list failed validation")
        raise _stored_invalid() from exc


@router.get("/{incident_id}", response_model=IncidentRecord)
def read_incident_record(
    incident_id: str,
    table: Annotated[Table, Depends(incidents_dependency)],
) -> IncidentRecord:
    try:
        record = get_incident(table, incident_id)
    except StorageError as exc:
        raise _storage_unavailable() from exc
    except DataIntegrityError as exc:
        logger.warning("Stored incident %s failed validation", incident_id)
        raise _stored_invalid() from exc
    if record is None:
        raise _missing()
    return record
