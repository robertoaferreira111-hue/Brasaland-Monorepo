/**
 * Browser adapters. sessionId is a tab-scoped UUID, not the access token.
 * userId is null when no staff session exists. When BrasalandSession reports
 * an access token, the adapter stores a separate opaque UUID. It never reads
 * the token, email, or name. The server does not expose an opaque staff id.
 */

import { createTelemetryService, type TelemetryService } from "./service.ts";
import type { TelemetryEventName, TelemetryProperties } from "./contract.ts";

export const DEFAULT_TELEMETRY_ENDPOINT = "http://localhost:8000/telemetry/events";
const SESSION_KEY = "brasaland.telemetry.session_id";
const USER_KEY = "brasaland.telemetry.user_id";

interface StaffSession {
  hasAccessToken?: () => boolean;
}

interface BrowserGlobals {
  sessionStorage?: Storage;
  crypto?: { randomUUID?: () => string };
  fetch?: typeof fetch;
  navigator?: { sendBeacon?: (url: string, body: BodyInit) => boolean };
  document?: Document;
  BrasalandSession?: StaffSession;
  NEXT_PUBLIC_TELEMETRY_ENDPOINT?: string;
  process?: { env?: { NEXT_PUBLIC_TELEMETRY_ENDPOINT?: string } };
}

function globals(): BrowserGlobals {
  return globalThis as BrowserGlobals;
}

export function readTelemetryEndpoint(source: { NEXT_PUBLIC_TELEMETRY_ENDPOINT?: string } | undefined): string {
  const value = source?.NEXT_PUBLIC_TELEMETRY_ENDPOINT?.trim();
  return value ? value : DEFAULT_TELEMETRY_ENDPOINT;
}

function endpointFromGlobals(): string {
  const current = globals();
  return readTelemetryEndpoint({
    NEXT_PUBLIC_TELEMETRY_ENDPOINT:
      current.process?.env?.NEXT_PUBLIC_TELEMETRY_ENDPOINT || current.NEXT_PUBLIC_TELEMETRY_ENDPOINT,
  });
}

function storage(): Storage | null {
  try {
    return globals().sessionStorage ?? null;
  } catch {
    return null;
  }
}

let memorySessionId: string | null = null;
let memoryUserId: string | null = null;

function newUuid(): string {
  const uuid = globals().crypto?.randomUUID?.();
  if (uuid) {
    return uuid;
  }
  return "00000000-0000-4000-8000-000000000000";
}

export function browserSessionId(): string {
  const store = storage();
  const existing = store?.getItem(SESSION_KEY) ?? memorySessionId;
  if (existing) {
    return existing;
  }
  const created = newUuid();
  memorySessionId = created;
  try {
    store?.setItem(SESSION_KEY, created);
  } catch {
    memorySessionId = created;
  }
  return created;
}

export function browserUserId(): string | null {
  const store = storage();
  const existing = store?.getItem(USER_KEY) ?? memoryUserId;
  if (existing) {
    return existing;
  }
  if (!globals().BrasalandSession?.hasAccessToken?.()) {
    return null;
  }
  const created = newUuid();
  memoryUserId = created;
  try {
    store?.setItem(USER_KEY, created);
  } catch {
    memoryUserId = created;
  }
  return created;
}

export function createBrowserTelemetry(): TelemetryService {
  return createTelemetryService({
    now: () => Date.now(),
    newId: () => newUuid(),
    getSessionId: () => browserSessionId(),
    getUserId: () => browserUserId(),
    endpoint: () => endpointFromGlobals(),
    async send(url, body) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      let received: number | null = null;
      try {
        const payload = (await response.json()) as { received?: unknown };
        if (typeof payload.received === "number") {
          received = payload.received;
        }
      } catch {
        received = null;
      }
      return { ok: response.ok, status: response.status, received };
    },
    sendBeacon(url, body) {
      const beacon = globals().navigator?.sendBeacon;
      if (!beacon) {
        return false;
      }
      const blob = new Blob([body], { type: "application/json" });
      return beacon(url, blob);
    },
    schedule(fn, ms) {
      return setTimeout(fn, ms) as unknown as number;
    },
    cancel(id) {
      clearTimeout(id);
    },
    subscribeHidden(listener) {
      const documentRef = globals().document;
      if (!documentRef) {
        return () => undefined;
      }
      const onChange = () => {
        if (documentRef.visibilityState === "hidden") {
          listener();
        }
      };
      documentRef.addEventListener("visibilitychange", onChange);
      return () => documentRef.removeEventListener("visibilitychange", onChange);
    },
  });
}

let browserService: TelemetryService | null = null;

function shared(): TelemetryService {
  if (!browserService) {
    browserService = createBrowserTelemetry();
  }
  return browserService;
}

export function track<E extends TelemetryEventName>(eventType: E, properties: TelemetryProperties[E]): void {
  shared().track(eventType, properties);
}

export function flush(): Promise<void> {
  return shared().flush();
}

export function stop(): void {
  shared().stop();
}
