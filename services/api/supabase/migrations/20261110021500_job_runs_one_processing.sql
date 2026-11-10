-- One processing row per job_name. This is the lock. A completed or failed
-- row does not match the predicate, so it releases the claim. This file does
-- not change reporting.pipeline_runs or public.telemetry_events.

create unique index if not exists idx_job_runs_one_processing
    on public.job_runs (job_name)
    where status = 'processing';
