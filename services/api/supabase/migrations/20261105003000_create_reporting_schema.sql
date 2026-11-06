-- Reporting destination for the Weekly Location Cost & Waste Report.
-- Does not alter public.telemetry_events and does not apply the proposed
-- append-only script.

create schema if not exists reporting;

revoke all on schema reporting from public;

create table reporting.weekly_location_performance (
  id uuid primary key default gen_random_uuid(),
  location_id text not null,
  country text not null,
  week_start date not null,
  total_purchase_cost numeric not null default 0,
  total_waste_cost numeric not null default 0,
  waste_ratio numeric not null default 0,
  stockout_events_count integer not null default 0,
  price_alert_events_count integer not null default 0,
  currency text not null,
  computed_at timestamptz not null default now(),
  unique (location_id, week_start)
);

create table reporting.pipeline_runs (
  run_id uuid primary key,
  pipeline_name text not null,
  trigger_type text not null,
  requested_week_start date not null,
  affected_weeks date[] not null,
  started_at timestamptz not null,
  finished_at timestamptz null,
  heartbeat_at timestamptz null,
  lease_expires_at timestamptz null,
  status text not null,
  last_completed_stage text null,
  watermark_from timestamptz not null,
  watermark_to timestamptz not null,
  rows_extracted integer not null,
  records_processed integer not null,
  rows_transformed integer not null,
  rows_loaded integer not null,
  rows_rejected integer not null,
  rows_skipped_duplicate integer not null,
  retry_count integer not null,
  duration_ms bigint null,
  error_stage text null,
  error_summary text null,
  pipeline_version text not null,
  constraint pipeline_runs_trigger_type_check
    check (trigger_type in ('schedule', 'manual', 'backfill')),
  constraint pipeline_runs_status_check
    check (status in ('running', 'success', 'failed'))
);

create unique index reporting_pipeline_runs_one_running
  on reporting.pipeline_runs (pipeline_name)
  where status = 'running';

revoke all on table reporting.weekly_location_performance from public;
revoke all on table reporting.pipeline_runs from public;

-- Supabase roles are absent on a plain Postgres server. Revoke only when
-- the role exists so this file can be applied to either.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    execute 'revoke all on schema reporting from anon';
    execute 'revoke all on table reporting.weekly_location_performance from anon';
    execute 'revoke all on table reporting.pipeline_runs from anon';
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    execute 'revoke all on schema reporting from authenticated';
    execute 'revoke all on table reporting.weekly_location_performance from authenticated';
    execute 'revoke all on table reporting.pipeline_runs from authenticated';
  end if;
end
$$;
