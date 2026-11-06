# Dev inventory seed

This folder is not imported by the business performance pipeline.

From `services/api`, with `DATABASE_URL` pointing at a non-production database that already has `public.telemetry_events`:

```bash
uv run python ../../data/dev/seed_inventory_events.py
uv run python ../../data/dev/seed_inventory_events.py late
```

The first command loads three complete UTC weeks of synthetic inventory events. The second loads one purchase dated inside the week of 2026-10-12. A repeated run inserts no extra rows. See `services/api/supabase/README.md` for the reporting migration that must be applied first.
