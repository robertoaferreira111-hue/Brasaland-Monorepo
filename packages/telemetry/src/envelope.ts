/**
 * Envelope construction. Callers never supply these fields.
 * eventId, sessionId, and requestId are UUIDs. timestamp is ISO 8601 UTC.
 * schemaVersion is 1.0.0. user_login_failed always uses a null userId.
 */

import {
  SCHEMA_VERSION,
  allowlistedProperties,
  type TelemetryEvent,
  type TelemetryEventName,
  type TelemetryProperties,
} from "./contract.ts";

const UUID_PATTERN =
  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/;

export interface EnvelopeInput<E extends TelemetryEventName> {
  eventType: E;
  properties: TelemetryProperties[E];
  nowMs: number;
  newId: () => string;
  sessionId: string;
  userId: string | null;
}

export function resolveUserId(eventType: TelemetryEventName, userId: string | null): string | null {
  if (eventType === "user_login_failed") {
    return null;
  }
  if (typeof userId !== "string") {
    return null;
  }
  const trimmed = userId.trim();
  if (!trimmed || trimmed.includes("@")) {
    return null;
  }
  return trimmed;
}

export function buildTelemetryEvent<E extends TelemetryEventName>(
  input: EnvelopeInput<E>,
): TelemetryEvent | null {
  const properties = allowlistedProperties(input.eventType, input.properties);
  if (!properties) {
    return null;
  }
  const eventId = input.newId();
  const requestId = input.newId();
  const sessionId = input.sessionId;
  if (!UUID_PATTERN.test(eventId) || !UUID_PATTERN.test(requestId) || !UUID_PATTERN.test(sessionId)) {
    return null;
  }
  const timestamp = new Date(input.nowMs).toISOString();
  if (!timestamp.endsWith("Z")) {
    return null;
  }
  return {
    eventId,
    timestamp,
    sessionId,
    userId: resolveUserId(input.eventType, input.userId),
    event_type: input.eventType,
    entity_action: input.eventType,
    schemaVersion: SCHEMA_VERSION,
    requestId,
    properties,
  };
}
