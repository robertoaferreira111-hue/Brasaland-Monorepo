/**
 * Maps existing backoffice behavior onto approved telemetry events.
 * Inventory events are not emitted here. This app has no inbound, outbound,
 * waste, threshold, or direct-stock behavior.
 */

import type { HttpMethod, OpsPage, TelemetryEventName, TelemetryProperties } from "./contract.ts";

export const BRIEF_MANDATORY_EVENTS = [
  "inbound_order_created",
  "outbound_order_created",
  "stock_waste_registered",
  "stock_threshold_triggered",
  "direct_stock_edit_rejected",
  "ingredient_price_variance_detected",
] as const;

const OPS_PAGES = new Set<string>([
  "login",
  "inbound_orders",
  "outbound_orders",
  "stock",
  "products",
  "suppliers",
  "account",
]);

const METHODS = new Set<string>(["GET", "POST", "PUT", "PATCH", "DELETE"]);

const ATTEMPTS_KEY = "brasaland.telemetry.login_attempts";

export type TrackFn = <E extends TelemetryEventName>(
  eventType: E,
  properties: TelemetryProperties[E],
) => void;

export interface ApiObservationInput {
  method: string;
  path: string;
  status: number;
  durationMs: number;
}

export function isOpsPage(value: string): value is OpsPage {
  return OPS_PAGES.has(value);
}

export function routeTemplate(path: string): string {
  const withoutQuery = path.split("?")[0] ?? "";
  let pathname = withoutQuery;
  if (withoutQuery.startsWith("http://") || withoutQuery.startsWith("https://")) {
    try {
      pathname = new URL(withoutQuery).pathname;
    } catch {
      pathname = withoutQuery;
    }
  }
  if (!pathname.startsWith("/")) {
    pathname = `/${pathname}`;
  }
  const trimmed = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  return trimmed.replace(/\/suppliers\/[^/]+/g, "/suppliers/{id}");
}

export function attemptBucket(attempts: number): "1" | "2-5" | "6+" {
  if (attempts <= 1) {
    return "1";
  }
  if (attempts <= 5) {
    return "2-5";
  }
  return "6+";
}

export function loginFailureProperties(
  status: number,
  attempts: number,
): TelemetryProperties["user_login_failed"] | null {
  let errorCode: TelemetryProperties["user_login_failed"]["error_code"] | null = null;
  if (status === 401) {
    errorCode = "invalid_credentials";
  } else if (status === 423) {
    errorCode = "account_locked";
  } else if (status === 400 || status === 422) {
    errorCode = "validation_error";
  }
  if (!errorCode) {
    return null;
  }
  const count = Number.isFinite(attempts) && attempts > 0 ? Math.floor(attempts) : 1;
  return { error_code: errorCode, attempt_bucket: attemptBucket(count) };
}

function apiErrorCode(status: number): TelemetryProperties["api_request_failed"]["error_code"] | null {
  if (status === 0) {
    return "network_error";
  }
  if (status === 401) {
    return "unauthorized";
  }
  if (status === 403) {
    return "forbidden";
  }
  if (status === 404) {
    return "not_found";
  }
  if (status === 408) {
    return "timeout";
  }
  if (status === 409) {
    return "conflict";
  }
  if (status === 400 || status === 422) {
    return "validation_error";
  }
  if (status >= 500 && status <= 599) {
    return "internal_error";
  }
  return null;
}

export function apiObservation(
  input: ApiObservationInput,
):
  | { eventType: "api_request_completed"; properties: TelemetryProperties["api_request_completed"] }
  | { eventType: "api_request_failed"; properties: TelemetryProperties["api_request_failed"] }
  | null {
  const method = input.method.toUpperCase();
  if (!METHODS.has(method)) {
    return null;
  }
  const routeTemplateValue = routeTemplate(input.path);
  if (!routeTemplateValue || routeTemplateValue.includes("/telemetry/events")) {
    return null;
  }
  const durationMs = Number.isFinite(input.durationMs) && input.durationMs >= 0 ? input.durationMs : 0;
  const httpMethod = method as HttpMethod;
  if (input.status >= 200 && input.status <= 299) {
    return {
      eventType: "api_request_completed",
      properties: {
        route_template: routeTemplateValue,
        method: httpMethod,
        status_code: input.status,
        duration_ms: durationMs,
      },
    };
  }
  const errorCode = apiErrorCode(input.status);
  if (!errorCode || input.status < 0 || input.status > 599) {
    return null;
  }
  return {
    eventType: "api_request_failed",
    properties: {
      route_template: routeTemplateValue,
      method: httpMethod,
      status_code: input.status,
      error_code: errorCode,
      duration_ms: durationMs,
    },
  };
}

export function pageLoadProperties(
  page: OpsPage,
  durationMs: number,
  connection?: string,
): TelemetryProperties["page_load_completed"] {
  const duration_ms = Number.isFinite(durationMs) && durationMs >= 0 ? durationMs : 0;
  if (
    connection === "wifi" ||
    connection === "cellular" ||
    connection === "ethernet" ||
    connection === "unknown"
  ) {
    return { page, duration_ms, connection_type: connection };
  }
  return { page, duration_ms };
}

interface AttemptStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export function observeCurrentPage(
  hooks: {
    notePage(page: string): void;
    notePageLoad(page: string, durationMs: number, connection?: string): void;
  },
  env: {
    page: string | undefined;
    durationMs: number;
    connection?: string;
    includeView?: boolean;
    includeLoad?: boolean;
  },
): void {
  if (!env.page) {
    return;
  }
  if (env.includeView !== false) {
    hooks.notePage(env.page);
  }
  if (env.includeLoad !== false) {
    hooks.notePageLoad(env.page, env.durationMs, env.connection);
  }
}

export function createCaptureHooks(track: TrackFn, storage: AttemptStorage | null) {
  function readAttempts(): number {
    const raw = storage?.getItem(ATTEMPTS_KEY);
    const value = Number(raw);
    return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
  }

  function writeAttempts(value: number): void {
    try {
      storage?.setItem(ATTEMPTS_KEY, String(value));
    } catch {
      // A storage failure must not block sign-in.
    }
  }

  return {
    noteLoginSuccess(): void {
      writeAttempts(0);
      track("user_logged_in", { auth_method: "password" });
    },
    noteLoginFailure(status: number): void {
      const next = readAttempts() + 1;
      writeAttempts(next);
      const properties = loginFailureProperties(status, next);
      if (!properties) {
        return;
      }
      track("user_login_failed", properties);
    },
    noteLogout(): void {
      track("user_logged_out", { reason: "user_action" });
    },
    noteApi(input: ApiObservationInput): void {
      const event = apiObservation(input);
      if (!event) {
        return;
      }
      track(event.eventType, event.properties);
    },
    notePage(page: string): void {
      if (!isOpsPage(page)) {
        return;
      }
      track("page_viewed", { page });
    },
    notePageLoad(page: string, durationMs: number, connection?: string): void {
      if (!isOpsPage(page)) {
        return;
      }
      track("page_load_completed", pageLoadProperties(page, durationMs, connection));
    },
  };
}
