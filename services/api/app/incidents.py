"""Read-only Brasaland incident records.

The CSV in data/raw is the only dataset. Blank cells become null. Rows are
not dropped or rewritten. Callers inside this process use list_incidents and
get_incident; the HTTP routes are a wrapper around those functions.
"""

from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from tinydb import Query
from tinydb.table import Table

from app.database import get_incidents_table, incidents_table, open_db
from app.errors import STORED_INCIDENT_INVALID, DataIntegrityError, StorageError

logger = logging.getLogger(__name__)

INCIDENT_ID_PATTERN = r"^BRS-\d{6}$"

IncidentStatus = Literal["OPEN", "CLOSED", "DISCARDED"]
IncidentCategory = Literal[
    "CUSTOMER_COMPLAINT",
    "EQUIPMENT",
    "SUPPLY",
    "FOOD_QUALITY",
    "STAFF",
]

CSV_FIELDS = (
    "incident_id",
    "date",
    "location_id",
    "category",
    "description",
    "status",
    "customer_id",
    "satisfaction_score",
    "reporter_id",
)


class IncidentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(pattern=INCIDENT_ID_PATTERN)
    date: date
    location_id: str | None
    category: IncidentCategory | None
    description: str | None
    status: IncidentStatus
    customer_id: str | None
    satisfaction_score: int | None = Field(default=None, ge=1, le=5)
    reporter_id: str


@dataclass(frozen=True)
class IncidentSeedResult:
    inserted: int
    total: int


def default_csv_path() -> Path:
    """Incident CSV. Inside Compose, BRASALAND_ROOT points at the mounted data tree."""
    root = os.environ.get("BRASALAND_ROOT", "").strip()
    if root:
        return Path(root) / "data" / "raw" / "incidents-brasaland.csv"
    return Path(__file__).resolve().parents[3] / "data" / "raw" / "incidents-brasaland.csv"


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _score(value: str | None) -> int | None:
    text = _blank(value)
    if text is None:
        return None
    if not text.isdigit():
        raise ValueError(f"satisfaction_score {text!r} is not an integer")
    return int(text)


def read_incident_csv(path: Path | None = None) -> list[IncidentRecord]:
    """Parse the real CSV. A row that cannot be represented raises ValueError."""
    csv_path = Path(path) if path is not None else default_csv_path()
    if not csv_path.is_file():
        raise ValueError(f"Incident CSV is missing: {csv_path}")
    try:
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or tuple(reader.fieldnames) != CSV_FIELDS:
                raise ValueError(
                    "Incident CSV columns do not match the Brasaland incident file."
                )
            records: list[IncidentRecord] = []
            seen: set[str] = set()
            for line_number, row in enumerate(reader, start=2):
                incident_id = (row.get("incident_id") or "").strip()
                try:
                    record = IncidentRecord(
                        incident_id=incident_id,
                        date=row.get("date") or "",
                        location_id=_blank(row.get("location_id")),
                        category=_blank(row.get("category")),
                        description=_blank(row.get("description")),
                        status=(row.get("status") or "").strip(),
                        customer_id=_blank(row.get("customer_id")),
                        satisfaction_score=_score(row.get("satisfaction_score")),
                        reporter_id=(row.get("reporter_id") or "").strip(),
                    )
                except (ValidationError, ValueError) as exc:
                    raise ValueError(
                        f"Incident CSV row {line_number} ({incident_id or 'no id'}) "
                        "does not match the incident record."
                    ) from exc
                if record.incident_id in seen:
                    raise ValueError(
                        f"Incident CSV repeats {record.incident_id} at row {line_number}."
                    )
                seen.add(record.incident_id)
                records.append(record)
    except OSError as exc:
        raise StorageError("Storage unavailable") from exc
    return records


def _document(record: IncidentRecord) -> dict:
    return record.model_dump(mode="json")


def _as_record(document: dict) -> IncidentRecord:
    payload = {key: value for key, value in document.items() if key != "doc_id"}
    try:
        return IncidentRecord.model_validate(payload)
    except ValidationError as exc:
        raise DataIntegrityError(STORED_INCIDENT_INVALID) from exc


def list_incidents(
    table: Table,
    *,
    status: str | None = None,
    category: str | None = None,
) -> list[IncidentRecord]:
    try:
        rows = table.all()
    except OSError as exc:
        logger.exception("Failed to list incidents")
        raise StorageError("Storage unavailable") from exc
    found: list[IncidentRecord] = []
    for document in rows:
        record = _as_record(dict(document))
        if status is not None and record.status != status:
            continue
        if category is not None and record.category != category:
            continue
        found.append(record)
    return found


def get_incident(table: Table, incident_id: str) -> IncidentRecord | None:
    try:
        document = table.get(Query().incident_id == incident_id)
    except OSError as exc:
        logger.exception("Failed to read incident %s", incident_id)
        raise StorageError("Storage unavailable") from exc
    if document is None:
        return None
    return _as_record(dict(document))


def get_incident_record(incident_id: str) -> IncidentRecord | None:
    """In-process read of one incident from the domain TinyDB file."""
    table_iter = get_incidents_table()
    table = next(table_iter)
    try:
        return get_incident(table, incident_id)
    finally:
        table_iter.close()


def seed_incidents(
    db_path: Path | None = None,
    csv_path: Path | None = None,
) -> IncidentSeedResult:
    """Insert CSV rows whose incident_id is not already stored."""
    records = read_incident_csv(csv_path)
    db = open_db(db_path)
    table = incidents_table(db)
    inserted = 0
    try:
        stored = {
            row.get("incident_id")
            for row in table.all()
            if isinstance(row.get("incident_id"), str)
        }
        for record in records:
            if record.incident_id in stored:
                continue
            try:
                table.insert(_document(record))
            except OSError as exc:
                raise StorageError("Storage unavailable") from exc
            stored.add(record.incident_id)
            inserted += 1
        return IncidentSeedResult(inserted=inserted, total=len(table))
    finally:
        db.close()
