-- Nightly job orchestration. This file does not alter public.telemetry_events
-- or reporting.pipeline_runs. Apply it in the Supabase SQL editor, with the
-- Supabase CLI, or with psql against the non-production DATABASE_URL.

create table if not exists public.job_runs (
    id uuid primary key default gen_random_uuid(),
    job_name text not null,
    target_date date not null,
    status text not null,
    started_at timestamptz null,
    finished_at timestamptz null,
    error_message text null,
    created_at timestamptz not null default now(),
    constraint job_runs_status_check
        check (status in ('pending', 'processing', 'completed', 'failed'))
);

create index if not exists idx_job_runs_job_name_status
    on public.job_runs (job_name, status);

create index if not exists idx_job_runs_job_name_target_date
    on public.job_runs (job_name, target_date);
