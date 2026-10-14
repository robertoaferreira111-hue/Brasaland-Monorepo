"""Validation rules for the supplier model and TinyDB writes."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.database import open_db, persist_supplier, suppliers_table
from app.models import Supplier
from app.seed import SUPPLIERS_SEED


def _record(**overrides) -> dict:
    data = dict(SUPPLIERS_SEED[0])
    data.update(overrides)
    return data


def test_supplier_fields_match_context_record():
    supplier = Supplier.from_client(SUPPLIERS_SEED[0])
    assert supplier.name == "Carnes del Valle S.A.S."
    assert supplier.country == "Colombia"
    assert supplier.categories == ["carne"]
    assert supplier.rate_per_unit == 28500.0
    assert supplier.currency == "COP"
    assert supplier.status == "active"
    assert supplier.contact_email == "ventas@carnesdelvalle.co"
    assert supplier.updated_at.tzinfo is not None


def test_client_updated_at_is_replaced():
    supplier = Supplier.from_client(_record(updated_at="2000-01-01T00:00:00+00:00"))
    assert supplier.updated_at.year != 2000
    assert supplier.updated_at >= datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_stored_updated_at_is_preserved():
    created = Supplier.from_client(SUPPLIERS_SEED[3])
    loaded = Supplier.from_storage(created.model_dump(mode="json"))
    assert loaded.updated_at == created.updated_at
    assert loaded.notes is None


@pytest.mark.parametrize("status", ["closed", "Active", ""])
def test_invalid_status_is_rejected(status):
    with pytest.raises(ValidationError):
        Supplier.from_client(_record(status=status))


@pytest.mark.parametrize("rate", [0, -1, -0.01])
def test_non_positive_rate_is_rejected(rate):
    with pytest.raises(ValidationError):
        Supplier.from_client(_record(rate_per_unit=rate))


def test_currency_must_match_country():
    with pytest.raises(ValidationError):
        Supplier.from_client(_record(country="Colombia", currency="USD"))
    with pytest.raises(ValidationError):
        Supplier.from_client(_record(country="USA", currency="COP", rate_per_unit=6.8))


def test_invalid_category_and_empty_list_are_rejected():
    with pytest.raises(ValidationError):
        Supplier.from_client(_record(categories=["meat"]))
    with pytest.raises(ValidationError):
        Supplier.from_client(_record(categories=[]))


def test_invalid_status_and_rate_are_not_persisted(tmp_path):
    db = open_db(tmp_path / "suppliers.json")
    table = suppliers_table(db)
    try:
        with pytest.raises(ValidationError):
            persist_supplier(table, _record(status="archived"))
        with pytest.raises(ValidationError):
            persist_supplier(table, _record(rate_per_unit=0))
        with pytest.raises(ValidationError):
            persist_supplier(table, _record(rate_per_unit=-5))
        assert len(table) == 0
    finally:
        db.close()
