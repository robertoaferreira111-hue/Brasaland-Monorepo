-- Append-only telemetry facts. This file does not remove or rewrite rows.
-- Apply it in the Supabase SQL editor or with the Supabase CLI.

create table if not exists public.telemetry_events (
    id uuid primary key default gen_random_uuid(),
    timestamp timestamptz not null,
    service text not null,
    event_type text not null,
    level text not null default 'info',
    value numeric null,
    message text null,
    tags jsonb not null default '{}'::jsonb
);

create index if not exists idx_telemetry_events_timestamp
    on public.telemetry_events (timestamp);

create index if not exists idx_telemetry_events_event_type
    on public.telemetry_events (event_type);

create index if not exists idx_telemetry_events_tags
    on public.telemetry_events using gin (tags);
