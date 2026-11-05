"""Dev reporting prerequisites: settings, migration text, and seed fixtures."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import clear_settings_cache, get_settings

_REPO = Path(__file__).resolve().parents[3]
_MIGRATIONS = _REPO / "services" / "api" / "supabase" / "migrations"
_REPORTING = _MIGRATIONS / "20261105003000_create_reporting_schema.sql"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def seed():
    sys.path.insert(0, str(_REPO / "services" / "api"))
    return _load("inventory_seed", _REPO / "data" / "dev" / "inventory_seed.py")


def test_database_url_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres@127.0.0.1:5432/brasaland")
    clear_settings_cache()
    try:
        assert (
            get_settings().database_url
            == "postgresql://postgres@127.0.0.1:5432/brasaland"
        )
    finally:
        clear_settings_cache()


def test_empty_database_url_is_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    clear_settings_cache()
    try:
        assert get_settings().database_url is None
    finally:
        clear_settings_cache()


def test_pipeline_db_module_does_not_import_the_seed() -> None:
    source = (_REPO / "data" / "pipelines" / "db.py").read_text(encoding="utf-8")
    assert "inventory_seed" not in source
    assert "seed_inventory_events" not in source


def test_reporting_migration_matches_the_briefing_and_run_record() -> None:
    sql = _REPORTING.read_text(encoding="utf-8")
    names = sorted(path.name for path in _MIGRATIONS.glob("*.sql"))
    assert names.index(_REPORTING.name) > names.index(
        "20261102180000_create_telemetry_events.sql"
    )
    assert "create table reporting.weekly_location_performance" in sql
    assert "unique (location_id, week_start)" in sql
    for column in (
        "run_id uuid primary key",
        "pipeline_name text not null",
        "trigger_type text not null",
        "requested_week_start date not null",
        "affected_weeks date[] not null",
        "started_at timestamptz not null",
        "finished_at timestamptz null",
        "heartbeat_at timestamptz null",
        "lease_expires_at timestamptz null",
        "status text not null",
        "last_completed_stage text null",
        "watermark_from timestamptz not null",
        "watermark_to timestamptz not null",
        "rows_extracted integer not null",
        "rows_transformed integer not null",
        "rows_loaded integer not null",
        "rows_rejected integer not null",
        "rows_skipped_duplicate integer not null",
        "retry_count integer not null",
        "duration_ms bigint null",
        "error_stage text null",
        "error_summary text null",
        "pipeline_version text not null",
    ):
        assert column in sql
    assert "where status = 'running'" in sql
    assert "revoke all on schema reporting from anon" in sql
    assert "revoke all on schema reporting from authenticated" in sql
    assert "grant " not in sql.lower()
    assert "create table public.telemetry_events" not in sql
    assert "alter table" not in sql.lower()


def test_main_seed_covers_weeks_locations_and_special_cases(seed) -> None:
    events = seed.main_events()
    rows = seed.prepare_rows(events)
    assert [row["id"] for row in rows] == [event["eventId"] for event in events]
    weeks = {seed.week_start_of(event["timestamp"]).isoformat() for event in events}
    assert weeks == set(seed.WEEKS)
    countries = {event["properties"]["country"] for event in events}
    assert countries == {"CO", "US"}
    co = {
        event["properties"]["location_id"]
        for event in events
        if event["properties"]["country"] == "CO"
    }
    us = {
        event["properties"]["location_id"]
        for event in events
        if event["properties"]["country"] == "US"
    }
    assert len(co) >= 3
    assert len(us) >= 3
    by_location: dict[str, set[str]] = {}
    for event in events:
        by_location.setdefault(event["properties"]["location_id"], set()).add(
            event["event_type"]
        )
    assert any(
        "stock_waste_registered" in types and "inbound_order_created" not in types
        for types in by_location.values()
    )
    assert any(
        "inbound_order_created" in types and "stock_waste_registered" not in types
        for types in by_location.values()
    )
    types = {event["event_type"] for event in events}
    assert types == {
        "inbound_order_created",
        "outbound_order_created",
        "stock_waste_registered",
        "stock_threshold_triggered",
        "ingredient_price_variance_detected",
    }
    assert "on conflict (id) do nothing" in seed.INSERT_SQL.lower()


def test_late_command_is_separate_and_idempotent_key(seed) -> None:
    main_ids = {event["eventId"] for event in seed.main_events()}
    late = seed.late_events()
    rows = seed.prepare_rows(late)
    assert len(late) == 1
    assert late[0]["eventId"] not in main_ids
    assert rows[0]["id"] == late[0]["eventId"]
    assert late[0]["event_type"] == "inbound_order_created"
    assert seed.week_start_of(late[0]["timestamp"]).isoformat() == "2026-10-12"


def test_invalid_fixtures_are_never_seeded(seed) -> None:
    seeded_ids = {
        event["eventId"] for event in seed.main_events() + seed.late_events()
    }
    fixtures = seed.invalid_fixtures()
    with pytest.raises(ValidationError):
        seed.prepare_rows(fixtures["missing_unit_cost"])
    with pytest.raises(ValidationError):
        seed.prepare_rows(fixtures["extra_tag"])
    with pytest.raises(seed.SeedRejected, match="country/currency mismatch"):
        seed.prepare_rows(fixtures["country_currency_mismatch"])
    with pytest.raises(seed.SeedRejected, match="conflicting payload"):
        seed.prepare_rows(fixtures["conflicting_payload"])
    for samples in fixtures.values():
        for event in samples:
            assert event["eventId"] not in seeded_ids
    source = (_REPO / "data" / "dev" / "seed_inventory_events.py").read_text(
        encoding="utf-8"
    )
    assert "invalid_fixtures" not in source
