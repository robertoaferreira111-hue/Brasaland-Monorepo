# Phase 3 verification

**Status: READY WITH USER ACTIONS**

The migration, bulk insert, per-event rejection, and update/delete rejection were executed against a local Postgres started by `pgserver` inside the test process. No Supabase project URL was available, so that hosted database was not modified.

## Command output

From `services/api`:

```text
uv run pytest -q --tb=line
78 passed, 4 warnings in 12.96s
```

The warnings are the existing Starlette `httpx` and HTTP 422 deprecations. The run includes `tests/test_telemetry_postgres.py`, which applies the migration, posts a mixed batch, reads the rows back, and attempts `UPDATE` and `DELETE`.

## Evaluation matrix

| Requirement | Result | Evidence |
| --- | --- | --- |
| Table columns and types | PASS | `information_schema.columns` returned the 11 columns and types asserted in `test_postgres_stores_representative_events_and_rejects_mutations`. The lesson's count of eight is not a list; the table keeps every `TelemetryEvent` field. |
| Three indexes | PASS | btree on `"timestamp"`, btree on `event_type`, `USING gin (tags)`. |
| `tags` keeps the property object | PASS | Read-back `tags` for the inbound row contained `location_id`, `country`, and `currency`, and did not contain `email`. |
| Stored event types | PASS | One batch stored `inbound_order_created`, `outbound_order_created`, and `user_login_failed`. |
| Database rejects UPDATE and DELETE | PASS | Both statements raised `telemetry_events cannot be updated or deleted`. The row count stayed 3. `telemetry_writer` has INSERT and does not have UPDATE or DELETE. |
| Valid events in a mixed batch are stored | PASS | HTTP 200, `received=4`, `stored=3`, `rejected=1`. |
| Invalid batch stores nothing | PASS | HTTP 200, `stored=0`, and the recording-store test records zero calls. |
| Empty batch | PASS | HTTP 200, all counts 0, no insert. |
| Malformed envelope | PASS | Non-JSON, a non-array `events`, and a missing `events` field return 422. |
| Database failure is not success | PASS | An unreachable `DATABASE_URL` returned HTTP 500 `Telemetry events were not stored`. The local table stayed empty. |
| One bulk insert | PASS | `bulk_insert_sql(3)` contains one `INSERT`. The Postgres test stored 3 accepted rows from one request. |
| `TelemetryEvent` unchanged | PASS | Class text matches `a5e0103`. |
| Body is not `list[TelemetryEvent]` | PASS | `TelemetryEnvelope.events` is `list[Any]`. |
| Frontend unchanged | PASS | No edits under `uis/` or `packages/`. |
| Backoffice generates the three events | BLOCKED | This tree has no telemetry client and no inbound or outbound screen. The three event payloads were posted to the API by the Postgres test instead. |
| Hosted Supabase project | NOT VERIFIED | No `SUPABASE_DB_URL` was set. The SQL was not applied to a hosted project. |

## User actions

1. In the Supabase SQL editor, run `supabase/migrations/20261027022000_create_telemetry_events.sql` once. It does not delete existing rows.
2. Set `SUPABASE_DB_URL` to that project's Postgres URI before starting the API.
3. Do not expect the current backoffice to emit `inbound_order_created` or `outbound_order_created`. Those screens are not in this repository.

## Git commands for you to run

These were not run.

```bash
git switch -c feature/telemetry-storage
git add \
  docs/telemetry/event-schemas.json \
  docs/telemetry/telemetry_events.sql \
  docs/telemetry/telemetry-events-schema.md \
  docs/telemetry/telemetry-persistence.md \
  docs/telemetry/phase-3-verification.md \
  supabase/migrations/20261027022000_create_telemetry_events.sql \
  services/api/app/main.py \
  services/api/app/models.py \
  services/api/app/routers/telemetry.py \
  services/api/app/telemetry_config.py \
  services/api/app/telemetry_schema.py \
  services/api/app/telemetry_store.py \
  services/api/pyproject.toml \
  services/api/uv.lock \
  services/api/tests/test_telemetry_persistence.py \
  services/api/tests/test_telemetry_postgres.py
git commit -m "$(cat <<'EOF'
Store accepted telemetry events in one Postgres insert.

EOF
)"
git push -u origin HEAD
gh pr create --title "Store telemetry events with a single Postgres insert." --body "$(cat <<'EOF'
## Summary
- Add the telemetry_events migration, including the GIN index on tags and triggers that reject UPDATE and DELETE.
- Validate each event on its own and insert the accepted rows with one INSERT statement.
- Prove the table, the mixed batch, and the rejected mutations against local Postgres. Hosted Supabase was not connected.

## Test plan
- [ ] From services/api, run `uv run pytest`
- [ ] Apply supabase/migrations/20261027022000_create_telemetry_events.sql to the Supabase project
- [ ] Start the API with SUPABASE_DB_URL set and post a mixed batch

EOF
)"
```
