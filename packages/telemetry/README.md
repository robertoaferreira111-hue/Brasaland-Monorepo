# Telemetry service

Reusable browser client for the approved Brasaland event contract in `docs/telemetry/event-schemas.json`. It does not define new event names and it does not write to a database.

## Interface

```ts
track(eventType, properties)
```

`eventType` is one of the 15 names in the schema. `properties` are only the allowlisted fields for that event. The service builds the envelope. Callers do not pass `eventId`, `timestamp`, `sessionId`, `userId`, `schemaVersion`, `requestId`, or `entity_action`.

`track` returns immediately. A rejected property set is not queued and does not throw.

`flush()` sends the current queue. `stop()` clears the flush timer, the retry timer, and the `visibilitychange` listener.

## Envelope

| Field | Rule |
| --- | --- |
| `eventId` | New UUID per event |
| `timestamp` | `Date.toISOString()`, UTC |
| `sessionId` | UUID kept for the browser tab in `sessionStorage` under `brasaland.telemetry.session_id`. It is not the access token. |
| `userId` | `null` for `user_login_failed`, for a signed-out page, and for any value that contains `@`. When `BrasalandSession.hasAccessToken()` is true, the service stores a separate opaque UUID in `brasaland.telemetry.user_id`. The staff API exposes email, not an opaque id, so the token and email are never copied. |
| `schemaVersion` | `1.0.0` |
| `requestId` | New UUID per event |
| `entity_action` | Same value as `event_type` |

## Transport

The POST URL is `NEXT_PUBLIC_TELEMETRY_ENDPOINT`. If that variable is empty, the client uses `http://localhost:8000/telemetry/events`.

The body is `{ "events": [ ...envelopes ] }`.

The queue is only in memory. A flush runs when 20 events are waiting or when 10 seconds have passed since the timer was armed, whichever happens first. A flush already in progress is not started again. Events tracked while that request is in flight stay in the queue and are sent later. They are not replaced by the in-flight batch.

A response removes a batch only when the status is 200 and `received` equals the number of events sent. Network errors, HTTP 408, HTTP 429, and HTTP 5xx are retried up to three times. The waits are 1s, then 2s, then 4s. After that the batch is dropped and `stats().droppedAfterRetry` increases. Other 4xx responses are not retried; `stats().rejectedByServer` increases. `track` does not throw when the endpoint is down.

When the page becomes hidden, the client calls `navigator.sendBeacon` with the same JSON body. A `true` result means the browser accepted the payload. It is not a server acknowledgement, and those events are not also sent with `fetch` (that would duplicate them). A `false` result, a missing beacon API, or a body over 60KB falls back to `fetch`. Beacon and retries can both deliver the same `eventId` more than once if a response is lost. This client does not promise exactly-once delivery. The stub does not deduplicate.

## Backoffice capture

`packages/telemetry/src/capture.ts` maps existing staff behavior onto approved events. `npm run build:telemetry` writes `uis/backoffice/js/telemetry.js`, which the backoffice pages load before `session.js`. Pages call `noteLoginSuccess`, `noteLoginFailure`, `noteLogout`, `noteApi`, and `noteCurrentPage`. They do not fill the envelope. The six briefing inventory events are not emitted: this repository has no inbound, outbound, waste, threshold, or direct-stock behavior. Coverage is listed in `docs/telemetry/event-coverage.md`.

## Tests

From the repository root:

```bash
npm run test:telemetry
npm run typecheck:telemetry
```
