/**
 * Classic-script entry for the staff backoffice.
 * Loaded before session.js so track() exists before the first API call.
 */

import { createCaptureHooks, observeCurrentPage, type TrackFn } from "./capture.ts";
import type { TelemetryEventName, TelemetryProperties } from "./contract.ts";
import { track } from "./browser.ts";

interface BackofficeTelemetry {
  noteLoginSuccess(): void;
  noteLoginFailure(status: number): void;
  noteLogout(): void;
  noteApi(input: { method: string; path: string; status: number; durationMs: number }): void;
  notePage(page: string): void;
  notePageLoad(page: string, durationMs: number, connection?: string): void;
  noteCurrentPage(): void;
}

interface BackofficeGlobals {
  document?: Document & { body?: HTMLElement & { dataset?: DOMStringMap } };
  performance?: Performance;
  navigator?: Navigator & { connection?: { type?: string } };
  sessionStorage?: Storage;
  BrasalandTelemetry?: BackofficeTelemetry;
  __brasalandPageNoted?: boolean;
}

function safeTrack<E extends TelemetryEventName>(eventType: E, properties: TelemetryProperties[E]): void {
  try {
    track(eventType, properties);
  } catch {
    // Telemetry must not affect the page.
  }
}

function connectionType(): string | undefined {
  const current = globalThis as BackofficeGlobals;
  return current.navigator?.connection?.type;
}

function durationMs(): number {
  const current = globalThis as BackofficeGlobals;
  const navigation = current.performance?.getEntriesByType("navigation")[0] as { duration?: number } | undefined;
  if (navigation && typeof navigation.duration === "number" && navigation.duration > 0) {
    return navigation.duration;
  }
  const elapsed = current.performance?.now();
  if (typeof elapsed === "number" && Number.isFinite(elapsed) && elapsed > 0) {
    return elapsed;
  }
  return 0;
}

export function installBackofficeTelemetry(trackFn: TrackFn = safeTrack): BackofficeTelemetry {
  const current = globalThis as BackofficeGlobals;
  let storage: Storage | null = null;
  try {
    storage = current.sessionStorage ?? null;
  } catch {
    storage = null;
  }
  const hooks = createCaptureHooks(trackFn, storage);
  const client: BackofficeTelemetry = {
    ...hooks,
    noteCurrentPage(): void {
      if (current.__brasalandPageNoted) {
        return;
      }
      current.__brasalandPageNoted = true;
      const page = current.document?.body?.dataset?.telemetryPage;
      observeCurrentPage(hooks, {
        page,
        durationMs: 0,
        includeLoad: false,
      });
      const sendLoad = () => {
        observeCurrentPage(hooks, {
          page,
          durationMs: durationMs(),
          connection: connectionType(),
          includeView: false,
        });
      };
      const documentRef = current.document;
      if (!documentRef || documentRef.readyState === "complete") {
        sendLoad();
        return;
      }
      window.addEventListener("load", sendLoad, { once: true });
    },
  };
  current.BrasalandTelemetry = client;
  return client;
}

installBackofficeTelemetry();
