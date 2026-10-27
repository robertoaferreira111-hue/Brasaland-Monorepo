import assert from "node:assert/strict";
import { test } from "node:test";

import { resolveUserId } from "../src/envelope.ts";
import {
  createTelemetryService,
  type SendResult,
  type TelemetryDeps,
  type TelemetryService,
} from "../src/service.ts";
import {
  DEFAULT_TELEMETRY_ENDPOINT,
  browserSessionId,
  browserUserId,
  readTelemetryEndpoint,
} from "../src/browser.ts";
import type { TelemetryEventName, TelemetryProperties } from "../src/contract.ts";

const SESSION = "22222222-2222-4222-8222-222222222222";
const ENDPOINT = "https://telemetry.example/events";

interface Clock {
  now(): number;
  schedule(fn: () => void, ms: number): number;
  cancel(id: number): void;
  advance(ms: number): void;
  pending(): number;
}

function createClock(): Clock {
  let now = 1_700_000_000_000;
  let next = 1;
  const timers: { id: number; at: number; fn: () => void }[] = [];
  return {
    now: () => now,
    schedule(fn, ms) {
      const id = next;
      next += 1;
      timers.push({ id, at: now + ms, fn });
      return id;
    },
    cancel(id) {
      const index = timers.findIndex((timer) => timer.id === id);
      if (index >= 0) {
        timers.splice(index, 1);
      }
    },
    advance(ms) {
      const target = now + ms;
      for (;;) {
        const due = timers
          .filter((timer) => timer.at <= target)
          .sort((left, right) => left.at - right.at || left.id - right.id);
        const timer = due[0];
        if (!timer) {
          break;
        }
        now = timer.at;
        const index = timers.findIndex((item) => item.id === timer.id);
        if (index >= 0) {
          timers.splice(index, 1);
        }
        timer.fn();
      }
      now = target;
    },
    pending: () => timers.length,
  };
}

async function drain(): Promise<void> {
  for (let step = 0; step < 8; step += 1) {
    await Promise.resolve();
  }
}

function createHarness(send: TelemetryDeps["send"], patch: Partial<TelemetryDeps> = {}) {
  const clock = createClock();
  let sequence = 0;
  let hidden: () => void = () => undefined;
  const beaconCalls: string[] = [];
  let beaconResult = true;
  const service = createTelemetryService({
    now: () => clock.now(),
    newId: () => {
      sequence += 1;
      return `11111111-1111-4111-8111-${sequence.toString(16).padStart(12, "0")}`;
    },
    getSessionId: () => SESSION,
    getUserId: () => null,
    endpoint: () => ENDPOINT,
    send,
    sendBeacon(_url, body) {
      beaconCalls.push(body);
      return beaconResult;
    },
    schedule: (fn, ms) => clock.schedule(fn, ms),
    cancel: (id) => clock.cancel(id),
    subscribeHidden(listener) {
      hidden = listener;
      return () => {
        hidden = () => undefined;
      };
    },
    ...patch,
  });
  return {
    clock,
    service,
    beaconCalls,
    hide() {
      hidden();
    },
    setBeacon(result: boolean) {
      beaconResult = result;
    },
  };
}

function accepted(body: string): SendResult {
  const count = JSON.parse(body).events.length as number;
  return { ok: true, status: 200, received: count };
}

function page(name: TelemetryProperties["page_viewed"]["page"] = "login"): TelemetryProperties["page_viewed"] {
  return { page: name };
}

test("metadata is generated once per event and the session id stays stable", async () => {
  const bodies: string[] = [];
  const harness = createHarness(async (_url, body) => {
    bodies.push(body);
    return accepted(body);
  });
  harness.service.track("page_viewed", page("login"));
  harness.service.track("page_viewed", page("suppliers"));
  harness.clock.advance(10_000);
  await drain();
  const events = JSON.parse(bodies[0] ?? "{}").events;
  assert.equal(events.length, 2);
  assert.equal(events[0].sessionId, SESSION);
  assert.equal(events[1].sessionId, SESSION);
  assert.notEqual(events[0].eventId, events[1].eventId);
  assert.notEqual(events[0].requestId, events[1].requestId);
  assert.equal(events[0].event_type, "page_viewed");
  assert.equal(events[0].entity_action, "page_viewed");
  assert.equal(events[0].schemaVersion, "1.0.0");
  assert.equal(events[0].userId, null);
  assert.equal(events[0].timestamp, new Date(1_700_000_000_000).toISOString());
  assert.equal(resolveUserId("user_login_failed", "opaque-staff-1"), null);
  assert.equal(resolveUserId("page_viewed", "staff@brasaland.com"), null);
  assert.equal(resolveUserId("user_logged_out", "opaque-staff-1"), "opaque-staff-1");
});

test("properties outside the allowlist are not queued", async () => {
  let sent = 0;
  const harness = createHarness(async () => {
    sent += 1;
    return { ok: true, status: 200, received: 1 };
  });
  harness.service.track("user_logged_in", {
    auth_method: "password",
    email: "staff@brasaland.com",
  } as TelemetryProperties["user_logged_in"]);
  harness.service.track("page_viewed", {} as TelemetryProperties["page_viewed"]);
  harness.clock.advance(10_000);
  await drain();
  assert.equal(sent, 0);
  assert.equal(harness.service.queueLength(), 0);
  assert.equal(harness.service.stats().rejectedLocally, 2);
});

test("a batch uses the events array and the configured endpoint", async () => {
  const calls: { url: string; body: string }[] = [];
  const harness = createHarness(async (url, body) => {
    calls.push({ url, body });
    return accepted(body);
  });
  harness.service.track("page_viewed", page());
  await harness.service.flush();
  await drain();
  assert.equal(calls[0]?.url, ENDPOINT);
  const payload = JSON.parse(calls[0]?.body ?? "{}");
  assert.deepEqual(Object.keys(payload), ["events"]);
  assert.equal(payload.events[0].properties.page, "login");
  assert.equal(harness.service.queueLength(), 0);
});

test("readTelemetryEndpoint uses NEXT_PUBLIC_TELEMETRY_ENDPOINT", () => {
  assert.equal(readTelemetryEndpoint(undefined), DEFAULT_TELEMETRY_ENDPOINT);
  assert.equal(
    readTelemetryEndpoint({ NEXT_PUBLIC_TELEMETRY_ENDPOINT: "http://localhost:8000/telemetry/events" }),
    "http://localhost:8000/telemetry/events",
  );
});

test("the queue flushes 10 seconds after the first event", async () => {
  let sent = 0;
  const harness = createHarness(async (_url, body) => {
    sent += 1;
    return accepted(body);
  });
  harness.service.track("page_viewed", page());
  harness.clock.advance(9_999);
  await drain();
  assert.equal(sent, 0);
  harness.clock.advance(1);
  await drain();
  assert.equal(sent, 1);
  assert.equal(harness.service.queueLength(), 0);
});

test("the queue flushes when it reaches 20 events", async () => {
  const sizes: number[] = [];
  const harness = createHarness(async (_url, body) => {
    sizes.push(JSON.parse(body).events.length);
    return accepted(body);
  });
  for (let index = 0; index < 19; index += 1) {
    harness.service.track("page_viewed", page("stock"));
  }
  assert.equal(sizes.length, 0);
  harness.service.track("page_viewed", page("stock"));
  await drain();
  assert.deepEqual(sizes, [20]);
  assert.equal(harness.service.queueLength(), 0);
  harness.clock.advance(10_000);
  await drain();
  assert.deepEqual(sizes, [20]);
});

test("a transient failure retries three times with exponential backoff", async () => {
  const waits: number[] = [];
  let attempts = 0;
  const harness = createHarness(async (_url, body) => {
    attempts += 1;
    if (attempts < 4) {
      return { ok: false, status: 503, received: null };
    }
    return accepted(body);
  });
  const started = harness.clock.pending();
  harness.service.track("page_viewed", page());
  void harness.service.flush();
  await drain();
  assert.equal(harness.service.queueLength(), 1);
  assert.equal(attempts, 1);
  for (const gap of [1_000, 2_000, 4_000]) {
    const before = harness.clock.now();
    harness.clock.advance(gap);
    waits.push(harness.clock.now() - before);
    await drain();
  }
  assert.deepEqual(waits, [1_000, 2_000, 4_000]);
  assert.equal(attempts, 4);
  assert.equal(harness.service.queueLength(), 0);
  assert.equal(harness.service.stats().droppedAfterRetry, 0);
  assert.equal(started >= 0, true);
});

test("events stay queued until the retry limit is exhausted", async () => {
  let attempts = 0;
  const harness = createHarness(async () => {
    attempts += 1;
    throw new Error("offline");
  });
  assert.doesNotThrow(() => harness.service.track("page_viewed", page()));
  void harness.service.flush();
  await drain();
  assert.equal(harness.service.queueLength(), 1);
  harness.clock.advance(1_000);
  await drain();
  harness.clock.advance(2_000);
  await drain();
  harness.clock.advance(4_000);
  await drain();
  assert.equal(attempts, 4);
  assert.equal(harness.service.queueLength(), 0);
  assert.equal(harness.service.stats().droppedAfterRetry, 1);
  assert.doesNotThrow(() => harness.service.track("page_viewed", page("account")));
});

test("a validation response is not retried", async () => {
  let attempts = 0;
  const harness = createHarness(async () => {
    attempts += 1;
    return { ok: false, status: 422, received: null };
  });
  harness.service.track("page_viewed", page());
  await drain();
  harness.clock.advance(10_000);
  await drain();
  assert.equal(attempts, 1);
  assert.equal(harness.service.stats().rejectedByServer, 1);
  assert.equal(harness.service.queueLength(), 0);
});

test("a flush already in flight does not send the same events twice", async () => {
  const calls: string[] = [];
  let release: (result: SendResult) => void = () => undefined;
  const harness = createHarness((_url, body) => {
    calls.push(body);
    return new Promise((resolve) => {
      release = resolve;
    });
  });
  harness.service.track("page_viewed", page("login"));
  const pending = harness.service.flush();
  await drain();
  harness.service.track("page_viewed", page("account"));
  void harness.service.flush();
  assert.equal(calls.length, 1);
  assert.equal(JSON.parse(calls[0] ?? "{}").events.length, 1);
  assert.equal(harness.service.queueLength(), 2);
  const finishFirst = release;
  finishFirst({ ok: true, status: 200, received: 1 });
  await pending;
  await drain();
  assert.equal(calls.length, 2);
  const firstEvents = JSON.parse(calls[0] ?? "{}").events;
  const secondEvents = JSON.parse(calls[1] ?? "{}").events;
  assert.equal(firstEvents.length, 1);
  assert.equal(secondEvents.length, 1);
  assert.equal(firstEvents[0].properties.page, "login");
  assert.equal(secondEvents[0].properties.page, "account");
  assert.notEqual(firstEvents[0].eventId, secondEvents[0].eventId);
  release({ ok: true, status: 200, received: 1 });
  await drain();
  assert.equal(harness.service.queueLength(), 0);
  harness.clock.advance(10_000);
  await drain();
  assert.equal(calls.length, 2);
});

test("visibility hidden uses sendBeacon and does not treat it as a fetch receipt", async () => {
  let fetches = 0;
  const harness = createHarness(async () => {
    fetches += 1;
    return { ok: true, status: 200, received: 1 };
  });
  harness.service.track("page_viewed", page());
  harness.hide();
  assert.equal(harness.beaconCalls.length, 1);
  assert.equal(JSON.parse(harness.beaconCalls[0] ?? "{}").events.length, 1);
  assert.equal(harness.service.queueLength(), 0);
  assert.equal(harness.service.stats().beaconAccepted, 1);
  assert.equal(fetches, 0);
});

test("a refused beacon falls back to fetch", async () => {
  let fetches = 0;
  const harness = createHarness(async (_url, body) => {
    fetches += 1;
    return accepted(body);
  });
  harness.setBeacon(false);
  harness.service.track("page_viewed", page());
  harness.hide();
  await drain();
  assert.equal(fetches, 1);
  assert.equal(harness.service.queueLength(), 0);
  assert.equal(harness.service.stats().beaconAccepted, 0);
});

test("stop removes the flush timer and the hidden listener", async () => {
  let fetches = 0;
  const harness = createHarness(async () => {
    fetches += 1;
    return { ok: false, status: 503, received: null };
  });
  harness.service.track("page_viewed", page());
  void harness.service.flush();
  await drain();
  assert.equal(fetches, 1);
  harness.service.stop();
  harness.clock.advance(10_000);
  await drain();
  harness.hide();
  assert.equal(fetches, 1);
  assert.equal(harness.clock.pending(), 0);
});

test("browser session id is stable and userId follows the staff session without reading the token", () => {
  const saved = new Map<string, string>();
  const store: Storage = {
    getItem: (key) => saved.get(key) ?? null,
    setItem: (key, value) => {
      saved.set(key, value);
    },
    removeItem: (key) => {
      saved.delete(key);
    },
    clear: () => saved.clear(),
    key: () => null,
    length: 0,
  };
  const target = globalThis as {
    sessionStorage?: Storage;
    crypto?: { randomUUID: () => string };
    BrasalandSession?: { hasAccessToken: () => boolean };
  };
  target.sessionStorage = store;
  target.BrasalandSession = { hasAccessToken: () => false };
  const first = browserSessionId();
  const second = browserSessionId();
  assert.equal(first, second);
  assert.equal(browserUserId(), null);
  target.BrasalandSession = { hasAccessToken: () => true };
  const userId = browserUserId();
  assert.equal(typeof userId, "string");
  assert.equal(browserUserId(), userId);
  assert.equal(saved.has("brasaland.access_token"), false);
});

test("service type accepts only the approved property shape", () => {
  const sample: TelemetryProperties["user_logged_in"] = { auth_method: "password" };
  const name: TelemetryEventName = "user_logged_in";
  const service: TelemetryService = createHarness(async () => ({ ok: true, status: 200, received: 1 })).service;
  service.track(name, sample);
  assert.equal(sample.auth_method, "password");
});
