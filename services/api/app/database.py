"""TinyDB initialization and validated supplier writes."""

from collections.abc import Iterator
from pathlib import Path

from tinydb import TinyDB
from tinydb.table import Table

from app.models import Supplier

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "suppliers.json"
SUPPLIERS_TABLE = "suppliers"


def open_db(path: Path | None = None) -> TinyDB:
    db_path = Path(path) if path is not None else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return TinyDB(db_path)


def suppliers_table(db: TinyDB) -> Table:
    return db.table(SUPPLIERS_TABLE)


def get_table() -> Iterator[Table]:
    db = open_db()
    try:
        yield suppliers_table(db)
    finally:
        db.close()


def persist_supplier(table: Table, data: dict) -> tuple[int, dict]:
    """Validate, then insert. Invalid data raises before TinyDB is changed."""
    supplier = Supplier.from_client(data)
    document = supplier.model_dump(mode="json")
    doc_id = table.insert(document)
    return doc_id, document


def list_supplier_documents(
    table: Table,
    *,
    country: str | None = None,
    category: str | None = None,
) -> list[tuple[int, dict]]:
    found: list[tuple[int, dict]] = []
    for document in table.all():
        if country is not None and document["country"] != country:
            continue
        if category is not None and category not in document["categories"]:
            continue
        found.append((document.doc_id, dict(document)))
    return found


def get_supplier_document(table: Table, supplier_id: int) -> dict | None:
    document = table.get(doc_id=supplier_id)
    if document is None:
        return None
    return dict(document)


def update_supplier_rate(
    table: Table, supplier_id: int, rate_per_unit: float
) -> dict | None:
    current = table.get(doc_id=supplier_id)
    if current is None:
        return None
    payload = dict(current)
    payload["rate_per_unit"] = rate_per_unit
    payload.pop("updated_at", None)
    supplier = Supplier.from_client(payload)
    document = supplier.model_dump(mode="json")
    table.update(document, doc_ids=[supplier_id])
    return document


def update_supplier_status(table: Table, supplier_id: int, status: str) -> dict | None:
    current = table.get(doc_id=supplier_id)
    if current is None:
        return None
    payload = dict(current)
    payload["status"] = status
    supplier = Supplier.from_storage(payload)
    document = supplier.model_dump(mode="json")
    table.update(document, doc_ids=[supplier_id])
    return document


def delete_supplier(table: Table, supplier_id: int) -> dict | None:
    current = table.get(doc_id=supplier_id)
    if current is None:
        return None
    document = dict(current)
    table.remove(doc_ids=[supplier_id])
    return document
