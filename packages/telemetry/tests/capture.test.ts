import assert from "node:assert/strict";
import { test } from "node:test";

import {
  BRIEF_MANDATORY_EVENTS,
  apiObservation,
  createCaptureHooks,
  observeCurrentPage,
  routeTemplate,
  type TrackFn,
} from "../src/capture.ts";
import type { TelemetryEventName, TelemetryProperties } from "../src/contract.ts";
import { createTelemetryService } from "../src/service.ts";

interface Recorded {
  eventType: string;
  properties: Record<string, unknown>;
}

function memory() {
  const data = new Map<string, string>();
  return {
    getItem(key: string) {
      return data.has(key) ? (data.get(key) ?? null) : null;
    },
    setItem(key: string, value: string) {
      data.set(key, value);
    },
  };
}

function recorder() {
  const events: Recorded[] = [];
  const track: TrackFn = (eventType, properties) => {
    events.push({ eventType, properties: { ...properties } });
  };
  return { events, track, hooks: createCaptureHooks(track, memory()) };
}

test("login failure uses an approved reason and no credentials", () => {
  const { events, hooks } = recorder();
  hooks.noteLoginFailure(401);
  hooks.noteLoginFailure(422);
  hooks.noteLoginFailure(423);
  hooks.noteLoginFailure(0);
  assert.equal(events.length, 3);
  assert.deepEqual(events[0], {
    eventType: "user_login_failed",
    properties: { error_code: "invalid_credentials", attempt_bucket: "1" },
  });
  assert.deepEqual(events[1].properties, { error_code: "validation_error", attempt_bucket: "2-5" });
  assert.deepEqual(events[2].properties, { error_code: "account_locked", attempt_bucket: "2-5" });
  for (const event of events) {
    assert.equal("email" in event.properties, false);
    assert.equal("password" in event.properties, false);
    assert.equal("token" in event.properties, false);
  }
});

test("attempt buckets advance and a successful login resets them", () => {
  const { events, hooks } = recorder();
  for (let attempt = 0; attempt < 6; attempt += 1) {
    hooks.noteLoginFailure(401);
  }
  hooks.noteLoginSuccess();
  hooks.noteLoginFailure(401);
  assert.equal(events[0]?.properties.attempt_bucket, "1");
  assert.equal(events[1]?.properties.attempt_bucket, "2-5");
  assert.equal(events[4]?.properties.attempt_bucket, "2-5");
  assert.equal(events[5]?.properties.attempt_bucket, "6+");
  assert.deepEqual(events[6], {
    eventType: "user_logged_in",
    properties: { auth_method: "password" },
  });
  assert.equal(events[7]?.properties.attempt_bucket, "1");
});

test("logout records the approved user action reason", () => {
  const { events, hooks } = recorder();
  hooks.noteLogout();
  assert.deepEqual(events, [{ eventType: "user_logged_out", properties: { reason: "user_action" } }]);
});

test("api observations keep route templates and drop the telemetry endpoint", () => {
  const completed = apiObservation({
    method: "get",
    path: "/suppliers?email=hidden@example.com",
    status: 200,
    durationMs: 12,
  });
  const missing = apiObservation({
    method: "GET",
    path: "http://127.0.0.1:8000/suppliers/42",
    status: 404,
    durationMs: 4,
  });
  const offline = apiObservation({ method: "POST", path: "/auth/login", status: 0, durationMs: 8 });
  const telemetry = apiObservation({
    method: "POST",
    path: "http://localhost:8000/telemetry/events",
    status: 200,
    durationMs: 1,
  });
  const unknown = apiObservation({ method: "GET", path: "/suppliers", status: 418, durationMs: 1 });
  assert.equal(routeTemplate("/suppliers/abc/?q=1"), "/suppliers/{id}");
  assert.deepEqual(completed, {
    eventType: "api_request_completed",
    properties: { route_template: "/suppliers", method: "GET", status_code: 200, duration_ms: 12 },
  });
  assert.equal(missing?.eventType, "api_request_failed");
  assert.equal(missing?.properties.route_template, "/suppliers/{id}");
  assert.equal(missing?.eventType === "api_request_failed" ? missing.properties.error_code : "", "not_found");
  assert.equal(offline?.eventType === "api_request_failed" ? offline.properties.error_code : "", "network_error");
  assert.equal(offline?.properties.status_code, 0);
  assert.equal(telemetry, null);
  assert.equal(unknown, null);
  const { events, hooks } = recorder();
  hooks.noteApi({ method: "GET", path: "/suppliers?email=hidden@example.com", status: 200, durationMs: 12 });
  assert.equal("email" in events[0]!.properties, false);
});

test("page capture accepts only the approved page enum", () => {
  const { events, hooks } = recorder();
  observeCurrentPage(hooks, { page: "suppliers", durationMs: 40, connection: "wifi" });
  observeCurrentPage(hooks, { page: "register", durationMs: 10 });
  observeCurrentPage(hooks, { page: "login", durationMs: -5, connection: "5g", includeView: false });
  assert.deepEqual(
    events.map((event) => event.eventType),
    ["page_viewed", "page_load_completed", "page_load_completed"],
  );
  assert.deepEqual(events[0]?.properties, { page: "suppliers" });
  assert.deepEqual(events[1]?.properties, { page: "suppliers", duration_ms: 40, connection_type: "wifi" });
  assert.deepEqual(events[2]?.properties, { page: "login", duration_ms: 0 });
});

test("auth and page hooks do not emit mandatory inventory events", () => {
  const { events, hooks } = recorder();
  hooks.noteLoginSuccess();
  hooks.noteLoginFailure(401);
  hooks.noteLogout();
  hooks.noteApi({ method: "POST", path: "/suppliers", status: 201, durationMs: 3 });
  observeCurrentPage(hooks, { page: "suppliers", durationMs: 1 });
  const seen = new Set(events.map((event) => event.eventType));
  for (const name of BRIEF_MANDATORY_EVENTS) {
    assert.equal(seen.has(name), false);
  }
});

test("a login failure is delivered by TelemetryService.track", async () => {
  const bodies: string[] = [];
  let sequence = 0;
  const userId = "33333333-3333-4333-8333-333333333333";
  const service = createTelemetryService({
    now: () => 1_700_000_000_000,
    newId: () => {
      sequence += 1;
      return `11111111-1111-4111-8111-${sequence.toString(16).padStart(12, "0")}`;
    },
    getSessionId: () => "22222222-2222-4222-8222-222222222222",
    getUserId: () => userId,
    endpoint: () => "http://localhost:8000/telemetry/events",
    async send(_url, body) {
      bodies.push(body);
      const parsed = JSON.parse(body) as { events: unknown[] };
      return { ok: true, status: 200, received: parsed.events.length };
    },
    sendBeacon: () => false,
    schedule: () => 1,
    cancel: () => undefined,
    subscribeHidden: () => () => undefined,
  });
  const hooks = createCaptureHooks(service.track.bind(service) as TrackFn, memory());
  hooks.noteLoginFailure(401);
  hooks.noteLoginSuccess();
  await service.flush();
  service.stop();
  const payload = JSON.parse(bodies[0] ?? "{}") as {
    events: Array<{ event_type: TelemetryEventName; userId: string | null; properties: TelemetryProperties[TelemetryEventName] }>;
  };
  assert.equal(payload.events[0]?.event_type, "user_login_failed");
  assert.equal(payload.events[0]?.userId, null);
  assert.deepEqual(payload.events[0]?.properties, {
    error_code: "invalid_credentials",
    attempt_bucket: "1",
  });
  assert.equal(payload.events[1]?.event_type, "user_logged_in");
  assert.equal(payload.events[1]?.userId, userId);
  assert.deepEqual(payload.events[1]?.properties, { auth_method: "password" });
});
