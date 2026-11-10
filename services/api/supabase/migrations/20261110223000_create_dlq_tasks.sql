-- Dead-letter rows for Celery tasks whose retries are exhausted.
-- Does not alter public.telemetry_events, public.job_runs, or reporting.pipeline_runs.

create table if not exists public.dlq_tasks (
    id uuid primary key default gen_random_uuid(),
    task_id text not null unique,
    task_name text not null,
    attempt integer not null,
    error_message text not null,
    created_at timestamptz not null default now()
);
