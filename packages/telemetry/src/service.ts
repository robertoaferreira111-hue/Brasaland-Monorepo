/**
 * In-memory batching client.
 * Flush at 20 events or 10 seconds, whichever comes first.
 * One initial POST plus up to three retries. Backoff is 1s, 2s, 4s.
 * A 200 whose received count matches the batch removes those events.
 * sendBeacon on hide is best-effort: a true result means the browser
 * accepted the payload, not that the server stored or acknowledged it.
 * Retries can deliver the same eventId more than once. This client does
 * not claim exactly-once delivery.
 */

import { buildTelemetryEvent } from "./envelope.ts";
import type { TelemetryBatchBody, TelemetryEvent, TelemetryEventName, TelemetryProperties } from "./contract.ts";

export const FLUSH_INTERVAL_MS = 10_000;
export const BATCH_SIZE = 20;
export const MAX_RETRIES = 3;
export const BACKOFF_BASE_MS = 1_000;
export const MAX_BEACON_BYTES = 60_000;

export interface SendResult {
  ok: boolean;
  status: number;
  received: number | null;
}

export interface TelemetryDeps {
  now(): number;
  newId(): string;
  getSessionId(): string;
  getUserId(): string | null;
  endpoint(): string;
  send(url: string, body: string): Promise<SendResult>;
  sendBeacon(url: string, body: string): boolean;
  schedule(fn: () => void, ms: number): number;
  cancel(id: number): void;
  subscribeHidden(listener: () => void): () => void;
  flushIntervalMs?: number;
  batchSize?: number;
  maxRetries?: number;
  backoffBaseMs?: number;
  maxBeaconBytes?: number;
}

export interface TelemetryStats {
  droppedAfterRetry: number;
  rejectedByServer: number;
  rejectedLocally: number;
  beaconAccepted: number;
}

export interface TelemetryService {
  track<E extends TelemetryEventName>(eventType: E, properties: TelemetryProperties[E]): void;
  flush(): Promise<void>;
  stop(): void;
  queueLength(): number;
  stats(): TelemetryStats;
}

export function createTelemetryService(deps: TelemetryDeps): TelemetryService {
  const flushIntervalMs = deps.flushIntervalMs ?? FLUSH_INTERVAL_MS;
  const batchSize = deps.batchSize ?? BATCH_SIZE;
  const maxRetries = deps.maxRetries ?? MAX_RETRIES;
  const backoffBaseMs = deps.backoffBaseMs ?? BACKOFF_BASE_MS;
  const maxBeaconBytes = deps.maxBeaconBytes ?? MAX_BEACON_BYTES;

  let queue: TelemetryEvent[] = [];
  let timer: number | null = null;
  let delayTimer: number | null = null;
  let releaseDelay: (() => void) | null = null;
  let inFlight: Promise<void> | null = null;
  let inFlightIds = new Set<string>();
  let flushAgain = false;
  let stopped = false;
  const stats: TelemetryStats = {
    droppedAfterRetry: 0,
    rejectedByServer: 0,
    rejectedLocally: 0,
    beaconAccepted: 0,
  };

  const unsubscribe = deps.subscribeHidden(() => {
    onHidden();
  });

  function armTimer(): void {
    if (stopped || timer !== null || queue.length === 0 || inFlight) {
      return;
    }
    timer = deps.schedule(() => {
      timer = null;
      void flush();
    }, flushIntervalMs);
  }

  function clearTimer(): void {
    if (timer !== null) {
      deps.cancel(timer);
      timer = null;
    }
    if (delayTimer !== null) {
      deps.cancel(delayTimer);
      delayTimer = null;
    }
    const release = releaseDelay;
    releaseDelay = null;
    release?.();
  }

  function removeEvents(events: TelemetryEvent[]): void {
    const ids = new Set(events.map((event) => event.eventId));
    queue = queue.filter((event) => !ids.has(event.eventId));
  }

  function delay(ms: number): Promise<void> {
    return new Promise((resolve) => {
      releaseDelay = resolve;
      delayTimer = deps.schedule(() => {
        delayTimer = null;
        releaseDelay = null;
        resolve();
      }, ms);
    });
  }

  async function deliver(snapshot: TelemetryEvent[]): Promise<void> {
    const body = JSON.stringify({ events: snapshot } satisfies TelemetryBatchBody);
    let retries = 0;
    while (!stopped) {
      let result: SendResult;
      try {
        result = await deps.send(deps.endpoint(), body);
      } catch {
        result = { ok: false, status: 0, received: null };
      }
      const acknowledged = result.ok && result.status === 200 && result.received === snapshot.length;
      if (acknowledged) {
        removeEvents(snapshot);
        return;
      }
      const transient = result.status === 0 || result.status === 408 || result.status === 429 || result.status >= 500;
      if (!transient) {
        stats.rejectedByServer += snapshot.length;
        removeEvents(snapshot);
        return;
      }
      if (retries >= maxRetries) {
        stats.droppedAfterRetry += snapshot.length;
        removeEvents(snapshot);
        return;
      }
      const wait = backoffBaseMs * 2 ** retries;
      retries += 1;
      await delay(wait);
    }
  }

  function flush(): Promise<void> {
    if (stopped) {
      return Promise.resolve();
    }
    if (inFlight) {
      flushAgain = true;
      return inFlight;
    }
    if (queue.length === 0) {
      return Promise.resolve();
    }
    clearTimer();
    const snapshot = queue.slice(0, batchSize);
    inFlightIds = new Set(snapshot.map((event) => event.eventId));
    const run = deliver(snapshot).finally(() => {
      inFlight = null;
      inFlightIds = new Set();
      if (stopped) {
        return;
      }
      if (flushAgain || queue.length >= batchSize) {
        flushAgain = false;
        void flush();
        return;
      }
      if (queue.length > 0) {
        armTimer();
      }
    });
    inFlight = run;
    return run;
  }

  function onHidden(): void {
    if (stopped || queue.length === 0) {
      return;
    }
    const pending = queue.filter((event) => !inFlightIds.has(event.eventId)).slice(0, batchSize);
    if (pending.length === 0) {
      return;
    }
    const body = JSON.stringify({ events: pending } satisfies TelemetryBatchBody);
    if (body.length > maxBeaconBytes) {
      void flush();
      return;
    }
    let accepted = false;
    try {
      accepted = deps.sendBeacon(deps.endpoint(), body);
    } catch {
      accepted = false;
    }
    if (accepted) {
      stats.beaconAccepted += pending.length;
      removeEvents(pending);
      if (queue.length === 0) {
        clearTimer();
      }
      return;
    }
    void flush();
  }

  return {
    track(eventType, properties) {
      if (stopped) {
        return;
      }
      try {
        const event = buildTelemetryEvent({
          eventType,
          properties,
          nowMs: deps.now(),
          newId: deps.newId,
          sessionId: deps.getSessionId(),
          userId: deps.getUserId(),
        });
        if (!event) {
          stats.rejectedLocally += 1;
          return;
        }
        queue.push(event);
        if (queue.length >= batchSize) {
          void flush();
          return;
        }
        armTimer();
      } catch {
        stats.rejectedLocally += 1;
      }
    },
    flush,
    stop() {
      stopped = true;
      clearTimer();
      unsubscribe();
    },
    queueLength() {
      return queue.length;
    },
    stats() {
      return { ...stats };
    },
  };
}
