# telemetry_events schema

The migration is [supabase/migrations/20261027022000_create_telemetry_events.sql](../../supabase/migrations/20261027022000_create_telemetry_events.sql). The same statements are in [telemetry_events.sql](./telemetry_events.sql). It creates the table only if it is missing. It does not drop the table or delete rows.

The lesson says the table has eight columns and names `event_type`, `timestamp`, `service`, and `tags`. It does not name the other four. This table has 11 columns so every `TelemetryEvent` field is stored, plus the lesson's `service` column and a database-generated `id`. `properties` is stored in `tags`.

| Column | Type | Source |
| --- | --- | --- |
| `id` | `bigint` identity, primary key | Database |
| `event_id` | `uuid` not null, unique | `eventId` |
| `timestamp` | `timestamptz` not null | `timestamp` |
| `session_id` | `uuid` not null | `sessionId` |
| `user_id` | `text` null | `userId` |
| `event_type` | `text` not null | `event_type` |
| `entity_action` | `text` not null, must equal `event_type` | `entity_action` |
| `schema_version` | `text` not null, must be `1.0.0` | `schemaVersion` |
| `request_id` | `uuid` not null | `requestId` |
| `service` | `text` not null | API setting `TELEMETRY_SERVICE`, default `brasaland-api`. The envelope has no service field. |
| `tags` | `jsonb` not null | `properties` |

Indexes: btree on `timestamp`, btree on `event_type`, GIN on `tags`.

`UPDATE` and `DELETE` are revoked from `PUBLIC` and from `telemetry_writer`. A before-row trigger raises `telemetry_events cannot be updated or deleted` for every role, including the table owner. `telemetry_writer` can `INSERT` and `SELECT`.

`TelemetryEvent` is unchanged from `origin/feat/telemetry-event-capture` (`a5e0103`). Allowlists are checked with `docs/telemetry/event-schemas.json` after `model_validate`, one event at a time.
