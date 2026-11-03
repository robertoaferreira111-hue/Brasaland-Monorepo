-- PROPOSED — do not apply until explicitly authorized.
-- Goal: database-level append-only for public.telemetry_events.
-- Apply only after reviewing Part A of the Phase 4 audit.
-- Does not DROP tables or DELETE rows.

-- 1) Client-facing roles: no UPDATE / DELETE (and no ALL via PUBLIC).
revoke all on table public.telemetry_events from public;
revoke update, delete on table public.telemetry_events from anon;
revoke update, delete on table public.telemetry_events from authenticated;
grant select, insert on table public.telemetry_events to anon, authenticated;

-- 2) Immutability triggers.
-- The Supabase service_role key bypasses RLS. Table REVOKE alone does not
-- stop UPDATE/DELETE when the API uses the service-role credential.
-- These triggers reject UPDATE and DELETE for every role, including
-- service_role. INSERT remains allowed.
create or replace function public.telemetry_events_reject_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'telemetry_events is append-only';
end;
$$;

drop trigger if exists telemetry_events_no_update on public.telemetry_events;
create trigger telemetry_events_no_update
  before update on public.telemetry_events
  for each row
  execute function public.telemetry_events_reject_mutation();

drop trigger if exists telemetry_events_no_delete on public.telemetry_events;
create trigger telemetry_events_no_delete
  before delete on public.telemetry_events
  for each row
  execute function public.telemetry_events_reject_mutation();

-- Optional verification after apply (run manually; expect errors on update/delete):
-- insert into public.telemetry_events (timestamp, service, event_type)
--   values (now(), 'api', 'permission_probe') returning id;
-- update public.telemetry_events set level = 'error' where id = '<id>';
-- delete from public.telemetry_events where id = '<id>';
