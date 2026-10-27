# Telemetry persistence endpoint

`POST /telemetry/events` validates each raw item with `TelemetryEvent.model_validate` and then `validate_event`. Accepted rows go out in one `INSERT` statement. `received = stored + rejected` on HTTP 200.

`tags` is the event `properties` object. `service` is `TELEMETRY_SERVICE` (`brasaland-api` unless the environment sets it).

The store reads `SUPABASE_DB_URL` or `DATABASE_URL`. One connection executes that single `INSERT` and commits it. A failed connection or statement rolls back and the response is HTTP 500 with `Telemetry events were not stored`. If neither URL is set, the store raises and the response is the same 500.

## Files

- `supabase/migrations/20261027022000_create_telemetry_events.sql`
- `docs/telemetry/event-schemas.json`
- `services/api/app/models.py` — `TelemetryEvent` unchanged; response counts added
- `services/api/app/telemetry_schema.py`
- `services/api/app/telemetry_config.py`
- `services/api/app/telemetry_store.py`
- `services/api/app/routers/telemetry.py`
- `services/api/app/main.py`
- `services/api/tests/test_telemetry_persistence.py`
- `services/api/tests/test_telemetry_postgres.py`

The frontend was not edited.
