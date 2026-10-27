-- Brasaland telemetry_events.
-- Re-running this file does not drop the table or delete rows.
--
-- Column sources:
--   id              database-generated primary key
--   event_id        TelemetryEvent.eventId
--   timestamp       TelemetryEvent.timestamp
--   session_id      TelemetryEvent.sessionId
--   user_id         TelemetryEvent.userId
--   event_type      TelemetryEvent.event_type
--   entity_action   TelemetryEvent.entity_action (must equal event_type)
--   schema_version  TelemetryEvent.schemaVersion
--   request_id      TelemetryEvent.requestId
--   service         lesson column; the API sets it, the envelope has no service field
--   tags            TelemetryEvent.properties
--
-- The lesson says the table has eight columns and names event_type, timestamp,
-- service, and tags. It does not name the other four. Dropping verified
-- TelemetryEvent fields to force that count would discard eventId, sessionId,
-- userId, entity_action, schemaVersion, or requestId. This table keeps them.

CREATE TABLE IF NOT EXISTS public.telemetry_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id uuid NOT NULL,
    "timestamp" timestamptz NOT NULL,
    session_id uuid NOT NULL,
    user_id text,
    event_type text NOT NULL,
    entity_action text NOT NULL,
    schema_version text NOT NULL,
    request_id uuid NOT NULL,
    service text NOT NULL,
    tags jsonb NOT NULL,
    CONSTRAINT telemetry_events_event_id_key UNIQUE (event_id),
    CONSTRAINT telemetry_events_entity_action_matches CHECK (entity_action = event_type),
    CONSTRAINT telemetry_events_schema_version_known CHECK (schema_version = '1.0.0')
);

CREATE INDEX IF NOT EXISTS telemetry_events_timestamp_idx
    ON public.telemetry_events ("timestamp");

CREATE INDEX IF NOT EXISTS telemetry_events_event_type_idx
    ON public.telemetry_events (event_type);

CREATE INDEX IF NOT EXISTS telemetry_events_tags_gin_idx
    ON public.telemetry_events USING gin (tags);

CREATE OR REPLACE FUNCTION public.telemetry_events_reject_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'telemetry_events cannot be updated or deleted';
END;
$$;

DROP TRIGGER IF EXISTS telemetry_events_no_update ON public.telemetry_events;
CREATE TRIGGER telemetry_events_no_update
    BEFORE UPDATE ON public.telemetry_events
    FOR EACH ROW
    EXECUTE FUNCTION public.telemetry_events_reject_mutation();

DROP TRIGGER IF EXISTS telemetry_events_no_delete ON public.telemetry_events;
CREATE TRIGGER telemetry_events_no_delete
    BEFORE DELETE ON public.telemetry_events
    FOR EACH ROW
    EXECUTE FUNCTION public.telemetry_events_reject_mutation();

REVOKE UPDATE, DELETE ON TABLE public.telemetry_events FROM PUBLIC;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'telemetry_writer') THEN
        CREATE ROLE telemetry_writer;
    END IF;
END
$$;

GRANT INSERT, SELECT ON TABLE public.telemetry_events TO telemetry_writer;
GRANT USAGE, SELECT ON SEQUENCE public.telemetry_events_id_seq TO telemetry_writer;
REVOKE UPDATE, DELETE ON TABLE public.telemetry_events FROM telemetry_writer;
