"""TinyDB initialization and validated supplier writes."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from tinydb import TinyDB
from tinydb.table import Table

from app.errors import StorageError
from app.models import Supplier

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "suppliers.json"
SUPPLIERS_TABLE = "suppliers"


def open_db(path: Path | None = None) -> TinyDB:
    db_path = Path(path) if path is not None else DEFAULT_DB_PATH
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return TinyDB(db_path)
    except OSError as exc:
        logger.exception("Failed to open supplier database")
        raise StorageError("Storage unavailable") from exc
    except ValueError as exc:
        # Corrupt JSON / TinyDB decode failures often surface as ValueError.
        logger.exception("Supplier database is unreadable")
        raise StorageError("Storage unavailable") from exc


def suppliers_table(db: TinyDB) -> Table:
    return db.table(SUPPLIERS_TABLE)


def get_table() -> Iterator[Table]:
    """Yield the suppliers table, or raise StorageError if the DB cannot be opened."""
    db = open_db()
    try:
        yield suppliers_table(db)
    finally:
        db.close()


def persist_supplier(table: Table, data: dict) -> tuple[int, dict]:
    """Validate, then insert. Invalid data raises before TinyDB is changed."""
    supplier = Supplier.from_client(data)
    document = supplier.model_dump(mode="json")
    try:
        doc_id = table.insert(document)
    except OSError as exc:
        logger.exception("Failed to insert supplier")
        raise StorageError("Storage unavailable") from exc
    return doc_id, document


def list_supplier_documents(
    table: Table,
    *,
    country: str | None = None,
    category: str | None = None,
) -> list[tuple[int, dict]]:
    try:
        rows = table.all()
    except OSError as exc:
        logger.exception("Failed to list suppliers")
        raise StorageError("Storage unavailable") from exc

    found: list[tuple[int, dict]] = []
    for document in rows:
        if country is not None and document.get("country") != country:
            continue
        categories = document.get("categories")
        if category is not None:
            if not isinstance(categories, list) or category not in categories:
                continue
        found.append((document.doc_id, dict(document)))
    return found


def get_supplier_document(table: Table, supplier_id: int) -> dict | None:
    try:
        document = table.get(doc_id=supplier_id)
    except OSError as exc:
        logger.exception("Failed to read supplier %s", supplier_id)
        raise StorageError("Storage unavailable") from exc
    if document is None:
        return None
    return dict(document)


def update_supplier_rate(
    table: Table, supplier_id: int, rate_per_unit: float
) -> dict | None:
    current = get_supplier_document(table, supplier_id)
    if current is None:
        return None
    payload = dict(current)
    payload["rate_per_unit"] = rate_per_unit
    payload.pop("updated_at", None)
    supplier = Supplier.from_client(payload)
    document = supplier.model_dump(mode="json")
    try:
        table.update(document, doc_ids=[supplier_id])
    except OSError as exc:
        logger.exception("Failed to update rate for supplier %s", supplier_id)
        raise StorageError("Storage unavailable") from exc
    return document


def update_supplier_status(table: Table, supplier_id: int, status: str) -> dict | None:
    current = get_supplier_document(table, supplier_id)
    if current is None:
        return None
    payload = dict(current)
    payload["status"] = status
    supplier = Supplier.from_storage(payload)
    document = supplier.model_dump(mode="json")
    try:
        table.update(document, doc_ids=[supplier_id])
    except OSError as exc:
        logger.exception("Failed to update status for supplier %s", supplier_id)
        raise StorageError("Storage unavailable") from exc
    return document


def delete_supplier(table: Table, supplier_id: int) -> dict | None:
    current = get_supplier_document(table, supplier_id)
    if current is None:
        return None
    document = dict(current)
    try:
        table.remove(doc_ids=[supplier_id])
    except OSError as exc:
        logger.exception("Failed to delete supplier %s", supplier_id)
        raise StorageError("Storage unavailable") from exc
    return document
