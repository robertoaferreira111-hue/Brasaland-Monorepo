"""Unit tests for the incident ticket lookup tool.

Success and not-found cases read a TinyDB file seeded from the real incident
CSV. Timeout and storage failure replace the read function. The Part 1 graph
is imported only to assert this tool is not a node.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "services" / "api"))

from services.agent.graph import agent_graph  # noqa: E402
from services.agent.tools.ticket_lookup import (  # noqa: E402
    HTTP_ERROR,
    NOT_FOUND,
    NOT_RECORDED,
    TIMEOUT,
    IncidentFields,
    lookup_ticket,
    resolve_lookup_timeout,
)
from services.agent.tools import ticket_lookup  # noqa: E402


@pytest.fixture
def incident_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "suppliers.json"
    monkeypatch.setattr("app.database.DEFAULT_DB_PATH", db_path)
    monkeypatch.delenv("BRASALAND_ROOT", raising=False)
    monkeypatch.delenv("INCIDENT_LOOKUP_TIMEOUT_SECONDS", raising=False)
    return db_path


def _seed() -> None:
    from app.incidents import seed_incidents

    seeded = seed_incidents()
    assert seeded.total == 100


def test_known_id_returns_the_stored_row(incident_db: Path) -> None:
    del incident_db
    _seed()
    output = lookup_ticket("BRS-000001")
    assert output.found is True
    assert output.error is None
    assert len(output.incidents) == 1
    row = output.incidents[0]
    assert row.incident_id == "BRS-000001"
    assert row.date == "2024-01-14"
    assert row.location_id == "COL-07"
    assert row.category == "FOOD_QUALITY"
    assert row.description == "Porción servida menor a la estándar del menú"
    assert row.status == "CLOSED"
    assert row.customer_id == "CLI-471507"
    assert row.satisfaction_score == 5
    assert row.reporter_id == "MGR-01"
    assert NOT_RECORDED not in row.model_dump().values()


def test_bare_number_uses_the_csv_id_width(incident_db: Path) -> None:
    del incident_db
    _seed()
    output = lookup_ticket(1)
    assert output.found is True
    assert output.incidents[0].incident_id == "BRS-000001"
    lowered = lookup_ticket("brs-000044")
    assert lowered.found is True
    assert lowered.incidents[0].incident_id == "BRS-000044"


def test_null_cells_are_not_recorded(incident_db: Path) -> None:
    del incident_db
    _seed()
    row = lookup_ticket("BRS-000044").incidents[0]
    assert row.location_id == NOT_RECORDED
    assert row.customer_id == NOT_RECORDED
    assert row.satisfaction_score == NOT_RECORDED
    assert row.category == "CUSTOMER_COMPLAINT"
    assert row.status == "OPEN"
    blank_category = lookup_ticket("BRS-000049").incidents[0]
    assert blank_category.category == NOT_RECORDED
    assert blank_category.location_id == "COL-03"
    blank_description = lookup_ticket("BRS-000079").incidents[0]
    assert blank_description.description == NOT_RECORDED
    assert blank_description.category == "EQUIPMENT"


def test_missing_id_is_not_found(incident_db: Path) -> None:
    del incident_db
    _seed()
    output = lookup_ticket("BRS-999999")
    assert output.found is False
    assert output.error == NOT_FOUND
    assert output.incidents == []


def test_number_absent_from_the_file_is_not_found(incident_db: Path) -> None:
    del incident_db
    _seed()
    output = lookup_ticket(482)
    assert output.found is False
    assert output.error == NOT_FOUND
    assert output.incidents == []


def test_text_that_is_not_an_id_is_not_found(incident_db: Path) -> None:
    del incident_db
    _seed()
    output = lookup_ticket("ticket 482")
    assert output.found is False
    assert output.error == NOT_FOUND
    assert output.incidents == []


def test_empty_store_has_no_embedded_copy(incident_db: Path) -> None:
    del incident_db
    output = lookup_ticket("BRS-000001")
    assert output.found is False
    assert output.error == NOT_FOUND


def test_read_ignores_brasaland_root(incident_db: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    del incident_db
    _seed()
    root = tmp_path / "compose-root"
    root.mkdir()
    monkeypatch.setenv("BRASALAND_ROOT", str(root))
    from app.incidents import default_csv_path

    csv_path = default_csv_path()
    assert csv_path == root / "data" / "raw" / "incidents-brasaland.csv"
    assert not csv_path.is_file()
    output = lookup_ticket(1)
    assert output.found is True
    assert output.error is None
    assert output.incidents[0].incident_id == "BRS-000001"


def test_filters_keep_matching_stored_rows(incident_db: Path) -> None:
    del incident_db
    _seed()
    output = lookup_ticket(status="CLOSED", category="FOOD_QUALITY")
    ids = [row.incident_id for row in output.incidents]
    assert output.found is True
    assert output.error is None
    assert "BRS-000001" in ids
    assert "BRS-000044" not in ids
    assert {row.status for row in output.incidents} == {"CLOSED"}
    assert {row.category for row in output.incidents} == {"FOOD_QUALITY"}


def test_id_outside_the_filter_is_not_found(incident_db: Path) -> None:
    del incident_db
    _seed()
    output = lookup_ticket("BRS-000001", status="OPEN")
    assert output.found is False
    assert output.error == NOT_FOUND


def test_unknown_filter_is_http_error(incident_db: Path) -> None:
    del incident_db
    _seed()
    output = lookup_ticket(status="OPENED")
    assert output.found is False
    assert output.error == HTTP_ERROR
    assert output.incidents == []


def test_storage_error_is_http_error(
    incident_db: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del incident_db
    from app.errors import StorageError

    def fail(incident_id, status, category):
        del incident_id, status, category
        raise StorageError("Storage unavailable")

    monkeypatch.setattr(ticket_lookup, "_load_records", fail)
    output = lookup_ticket("BRS-000001")
    assert output.found is False
    assert output.error == HTTP_ERROR
    assert output.incidents == []


def test_timeout_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    release = threading.Event()

    def block(incident_id, status, category):
        del incident_id, status, category
        release.wait(30)
        return []

    monkeypatch.setattr(ticket_lookup, "_load_records", block)
    output = lookup_ticket("BRS-000001", timeout_seconds=3)
    assert output.found is False
    assert output.error == TIMEOUT
    assert output.incidents == []
    release.set()


def test_timeout_outside_the_window_does_not_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(incident_id, status, category):
        del incident_id, status, category
        raise AssertionError("storage was read")

    monkeypatch.setattr(ticket_lookup, "_load_records", fail)
    output = lookup_ticket("BRS-000001", timeout_seconds=2)
    assert output.error == HTTP_ERROR
    assert output.found is False


def test_timeout_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INCIDENT_LOOKUP_TIMEOUT_SECONDS", raising=False)
    assert resolve_lookup_timeout(None) == 5.0
    assert resolve_lookup_timeout(4) == 4.0
    monkeypatch.setenv("INCIDENT_LOOKUP_TIMEOUT_SECONDS", "4")
    assert resolve_lookup_timeout(None) == 4.0


def test_contract_exposes_only_incident_api_fields() -> None:
    names = set(IncidentFields.model_fields)
    assert names == {
        "incident_id",
        "date",
        "location_id",
        "category",
        "description",
        "status",
        "customer_id",
        "satisfaction_score",
        "reporter_id",
    }


def test_graph_nodes_include_the_ticket_path() -> None:
    names = {name for name in agent_graph.nodes if not str(name).startswith("__")}
    assert names == {
        "receive_question",
        "route_intent",
        "retrieve",
        "query",
        "lookup_ticket",
        "handle_tool_failure",
        "synthesize_answer",
    }
