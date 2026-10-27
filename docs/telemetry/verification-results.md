# Verification results

Recorded 26 Oct 2026 from the commands and the live login-page request below. These values replace the submission placeholders.

## Pull request

Title: `feat: telemetry event capture`

## Summary

- Add the FastAPI telemetry batch-validation endpoint.
- Add the frontend TelemetryService with metadata, batching, delivery, and retry behavior.
- Instrument the approved technical and business events that have a real trigger in this repository.
- Add automated tests and document verification results.

## Validation

- Backend tests: `uv run pytest -q` from `services/api` — 75 passed, 6 warnings, in 6.66s. The 10 telemetry tests are included. Warnings are existing Starlette deprecations for `httpx` TestClient and `HTTP_422_UNPROCESSABLE_ENTITY`.
- Frontend tests: `npm run test:telemetry` — 27 passed, 0 failed, 0 skipped, in 939ms.
- Production build: `npm run build:telemetry` — esbuild wrote `uis/backoffice/js/telemetry.js`, 26.5kb, done in 49ms.
- Endpoint response: `POST http://localhost:8000/telemetry/events` returned HTTP 200 with body `{"received":2}`. The batch was `page_viewed` and `page_load_completed` for `page=login`. `page_load_completed.duration_ms` was 165.4. Both envelopes used `schemaVersion` `1.0.0`, `entity_action` equal to `event_type`, and `userId` null. The request body contained no email or password. The API log line was `telemetry events received count=2 event_types=page_viewed,page_load_completed`, followed by `POST /telemetry/events HTTP/1.1" 200 OK`.
- Instrumentation coverage: 7 of 15 approved events are captured at a real application trigger and covered by tests. Outstanding: the 6 briefing inventory events, plus `product_validation_failed` and `workflow_abandoned`. Those eight have no screen or route in this repository. Supplier directory actions are not used as substitutes.

## Scope

- No database persistence introduced. `test_valid_batch_does_not_open_a_database` refuses `TinyDB` during a valid batch.
- No prohibited personal data included in telemetry. Login-failure properties are `error_code` and `attempt_bucket` only. The live page batch had `userId` null and no email or password.

## Evidence

- Network capture from the staff login page after the 10-second flush, through the browser DevTools protocol: status 200, response `{"received":2}`, URL `http://localhost:8000/telemetry/events`.
- The embedded browser does not open the Chrome Network panel, so a panel screenshot was not produced. The protocol capture and the API log are the response evidence.
- Captured events:

```json
{
  "url": "http://localhost:8000/telemetry/events",
  "status": 200,
  "responseText": "{\"received\":2}",
  "events": [
    {
      "event_type": "page_viewed",
      "entity_action": "page_viewed",
      "userId": null,
      "schemaVersion": "1.0.0",
      "properties": { "page": "login" }
    },
    {
      "event_type": "page_load_completed",
      "entity_action": "page_load_completed",
      "userId": null,
      "schemaVersion": "1.0.0",
      "properties": { "page": "login", "duration_ms": 165.4 }
    }
  ]
}
```

## Coverage

| Event | Status |
| --- | --- |
| `user_logged_in` | Captured after a successful `POST /auth/login` |
| `user_login_failed` | Captured for HTTP 401, 400, 422, and 423 |
| `user_logged_out` | Captured before the token is cleared |
| `page_viewed` | Captured for login, suppliers, and account |
| `page_load_completed` | Captured for those same pages |
| `api_request_completed` | Captured for caller-facing 2xx responses |
| `api_request_failed` | Captured for caller-facing failures, including status 0 |
| `inbound_order_created` | Outstanding. No inbound-order behavior |
| `outbound_order_created` | Outstanding. No outbound-order behavior |
| `stock_waste_registered` | Outstanding. No waste behavior |
| `stock_threshold_triggered` | Outstanding. No stock-threshold behavior |
| `direct_stock_edit_rejected` | Outstanding. No direct-edit behavior |
| `ingredient_price_variance_detected` | Outstanding. No price-variance behavior |
| `product_validation_failed` | Outstanding. No product form |
| `workflow_abandoned` | Outstanding. No inventory workflow UI |
