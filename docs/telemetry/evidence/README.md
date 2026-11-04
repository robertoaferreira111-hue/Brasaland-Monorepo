# Telemetry storage live evidence

Captured 2026-11-03 against a personal Supabase free-tier project.

## Mixed-batch HTTP response

```json
{"received":2,"stored":1,"rejected":1}
```

Technical seed batch: `{"received":4,"stored":4,"rejected":0}`.

## Screenshots

- `supabase-telemetry-events-id-timestamp-service.jpg` — five rows (`id`, `timestamp`, `service`).
- `supabase-telemetry-events-type-level-message.jpg` — same rows (`event_type`, `level`, `value`, `message`); all technical.

No business/inventory rows: capture instrumentation for mandatory Brasaland business events is not available yet (inventory screens missing).
