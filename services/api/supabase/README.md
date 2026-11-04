# Telemetry storage (Supabase)

Apply the migration, then point the API at the project. Do not put the
service-role key in a `NEXT_PUBLIC_` variable.

## 1. Create the table

Run this file in the Supabase SQL editor (or with the Supabase CLI):

`migrations/20261102180000_create_telemetry_events.sql`

It creates `public.telemetry_events` with eight columns and three indexes.
It does not drop tables or delete rows.

## 2. API environment

Copy from the repo root `.env.example` into an ignored `.env` file:

- `SUPABASE_URL` — project URL (for example `https://xxxx.supabase.co`)
- `SUPABASE_SERVICE_ROLE_KEY` — service-role key from the Supabase dashboard

Restart `services/api` after setting them. Without both values the ingest
route returns HTTP 500 `Storage unavailable` and does not write rows.

## 3. Smoke check

With the API on port 8000:

```bash
curl -s -X POST "http://127.0.0.1:8000/telemetry/events" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "eventId": "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6f",
        "timestamp": "2026-11-02T22:00:00Z",
        "sessionId": null,
        "userId": null,
        "event_type": "staff_login_failed",
        "entity_action": "staff_session.login_failed",
        "schemaVersion": "1.0.0",
        "requestId": "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6a",
        "properties": { "outcome": "invalid_credentials" }
      },
      {
        "eventId": "not-a-uuid",
        "timestamp": "bad",
        "sessionId": null,
        "userId": null,
        "event_type": "",
        "entity_action": "x",
        "schemaVersion": "1.0.0",
        "requestId": "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6b",
        "properties": {}
      }
    ]
  }'
```

Expected body: `{"received":2,"stored":1,"rejected":1}`.

Then in Supabase:

```sql
select event_type, timestamp, service, level, tags
from public.telemetry_events
order by timestamp desc
limit 20;
```

## Mapping notes

- `id` is the producer `eventId`. The schema requires that value to be a UUID, which matches the `telemetry_events.id` column. A second delivery of the same `eventId`, in one batch or a later batch, does not insert another row and does not return an error.
- `received` is the number of events in the request. `rejected` is the number that fail validation, including a missing or non-UUID `eventId`. `stored` is the number of rows newly inserted by that request. A repeated valid `eventId` is not rejected and is not included in `stored`.
- `tags` is the event `properties` object only (allowlist keys from
  `docs/telemetry/telemetry-plan.md`).
- Envelope fields `sessionId`, `userId`, `schemaVersion`, and `requestId`
  are not copied into `tags`. `eventId` is stored as `id`, not inside `tags`.
  The plan’s analytics dimensions for rollups are `location_id`, `country`,
  and `timestamp`.
- `service` is the constant `api` (this writer).
- `message` is `entity_action`.
- `level` is `error` for failure events in the catalogue, otherwise `info`.
- Application code has no UPDATE or DELETE route for this table.

## Append-only at the database (proposed)

`migrations/PROPOSED_20261102190000_telemetry_events_append_only.sql` is
**not** applied by default. It waits for explicit authorization.

Why it exists: the API uses `SUPABASE_SERVICE_ROLE_KEY`. That role bypasses
RLS, so “no UPDATE/DELETE routes in FastAPI” is not database immutability.
The proposed script:

1. Revokes UPDATE/DELETE from `anon` / `authenticated`.
2. Adds BEFORE UPDATE / BEFORE DELETE triggers that reject mutations for
   every role, including `service_role`.

Do not run it until the live project owner approves it.

## Live verification checklist (user-side)

1. Apply `20261102180000_create_telemetry_events.sql` in the SQL editor.
2. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in a local ignored `.env`.
3. Start the API and POST inbound, outbound, and technical events.
4. Confirm ≥5 rows and inspect `event_type`, `timestamp`, `service`, `level`, `tags`.
5. Run the mixed-batch curl above; expect `{"received":2,"stored":1,"rejected":1}`.
6. Optionally apply the proposed append-only SQL after approval.
7. Docker (when the daemon is up):

```bash
docker build --target production -t brasaland-api ./services/api
docker run --rm -p 8000:8000 \
  -e SUPABASE_URL \
  -e SUPABASE_SERVICE_ROLE_KEY \
  brasaland-api
docker exec <container> python -c "from pathlib import Path; p=Path('/app/app/telemetry_event_schema.json'); print(p.exists(), p.stat().st_size)"
```
