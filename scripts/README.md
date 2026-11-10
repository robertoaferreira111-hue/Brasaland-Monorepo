# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

## Nightly telemetry export

`nightly_export.py` is a separate process from the FastAPI API. It exports one UTC day of `public.telemetry_events` to `data/raw/telemetry_YYYY-MM-DD.csv`, then runs `data/pipelines/pipeline.py`. The schedule is [`nightly_export.crontab`](./nightly_export.crontab).

Cron owns the clock. A scheduler inside the API process would stop when the API stops, and it would tie the export to a request worker. The crontab starts the script at 02:00 UTC whether or not the API is running. `CRON_TZ=UTC` keeps that hour on UTC for cron implementations that honor it. If a host ignores `CRON_TZ`, convert 02:00 UTC to that host's local hour. The script's target date does not use the host zone: an empty `TARGET_DATE` is yesterday in UTC.

The crontab does not contain credentials. Copy [`nightly_export.env.example`](./nightly_export.env.example) to `$HOME/.config/brasaland/nightly_export.env` and set `DATABASE_URL` and a `PATH` that includes `uv` there. The crontab loads that file with `set -a` and `.`. Output is appended to `$HOME/Library/Logs/brasaland-nightly_export.log`.

Installing the line into the live crontab is optional. The command in the file is the one to run.

A hard kill (`SIGKILL`) does not run the script's failure path. The partial unique index then blocks later runs while a row stays `processing`. An operator releases it with:

```sql
update public.job_runs
set status = 'failed',
    finished_at = now(),
    error_message = 'operator release after a hard kill left this row processing'
where job_name = 'nightly_export'
  and status = 'processing';
```

There is no automatic expiry.

### Tests

`services/api` collects only its own `tests/` directory. From the repository root, with `DATABASE_URL` set for the Postgres suites:

```bash
(cd services/api && uv run pytest)
uv run --project services/api pytest services/job_runner/tests
uv run --project services/api pytest scripts/tests
```

> _Spanish version: [README.es.md](./README.es.md)._
