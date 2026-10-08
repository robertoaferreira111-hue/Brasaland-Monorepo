"""Repeatable seed of the 15 Brasaland suppliers."""

from app.database import open_db, suppliers_table
from app.models import VALID_CATEGORIES, VALID_STATUSES, Supplier
from app.seed import SUPPLIERS_SEED, seed_suppliers


def test_seed_inserts_context_records_once(tmp_path):
    db_path = tmp_path / "suppliers.json"

    first = seed_suppliers(db_path)
    second = seed_suppliers(db_path)

    assert len(SUPPLIERS_SEED) == 15
    assert first.inserted == 15
    assert first.total == 15
    assert second.inserted == 0
    assert second.total == 15

    db = open_db(db_path)
    try:
        rows = suppliers_table(db).all()
    finally:
        db.close()

    assert len(rows) == 15
    assert len({row["name"] for row in rows}) == 15
    stored = {row["name"]: row for row in rows}
    for record in SUPPLIERS_SEED:
        row = stored[record["name"]]
        supplier = Supplier.from_storage(row)
        assert supplier.country == record["country"]
        assert supplier.categories == record["categories"]
        assert supplier.rate_per_unit == record["rate_per_unit"]
        assert supplier.currency == record["currency"]
        assert supplier.status == record["status"]
        assert supplier.contact_email == record["contact_email"]
        assert supplier.notes == record.get("notes")
        assert supplier.status in VALID_STATUSES
        assert all(category in VALID_CATEGORIES for category in supplier.categories)
        assert "updated_at" in row
