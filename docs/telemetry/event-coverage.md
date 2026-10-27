# Event coverage

Source of event names and property allowlists: `docs/telemetry/telemetry-plan.md` and `docs/telemetry/event-schemas.json`. Capture goes through `TelemetryService.track()`. Pages do not set `eventId`, `timestamp`, `sessionId`, `userId`, `schemaVersion`, `requestId`, or `entity_action`.

The six briefing events stay uncaptured. `services/api` and `uis/backoffice` have no inbound order, outbound order, waste, stock-threshold, or direct-stock behavior. The supplier directory is not used as a substitute.

Uncaught errors, unhandled rejections, and Web Vitals are not in the approved event vocabulary, so no handlers were added for them. Page performance uses `page_load_completed`.

| Event | Property allowlist | Capture point | Mechanism | Verification | Status |
| --- | --- | --- | --- | --- | --- |
| `inbound_order_created` | `location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit`, `currency`, `supplier_id`, `unit_cost`, `inbound_order_id` | None. No inbound-order screen or route. | Not emitted. | `auth and page hooks do not emit mandatory inventory events` | Not captured |
| `outbound_order_created` | Shared inventory properties, `outbound_order_id`, `reason=prep_consumption` | None. No outbound-order screen or route. | Not emitted. | Same test | Not captured |
| `stock_waste_registered` | Shared inventory properties, `outbound_order_id`, `reason` `expired` \| `kitchen_error` \| `theft_suspected` | None. No waste screen or route. | Not emitted. | Same test | Not captured |
| `stock_threshold_triggered` | Shared inventory properties, `minimum_quantity` | None. No stock screen or route. | Not emitted. | Same test | Not captured |
| `direct_stock_edit_rejected` | Shared inventory properties, `rejection_code=direct_edit_forbidden` | None. No direct-edit screen or route. | Not emitted. | Same test | Not captured |
| `ingredient_price_variance_detected` | Shared inventory properties, `supplier_id`, `unit_cost`, `historical_unit_cost`, `variance_pct`, `variance_threshold_pct`, `inbound_order_id` | None. No price-variance behavior. | Not emitted. | Same test | Not captured |
| `user_logged_in` | `auth_method=password` | `uis/backoffice/js/login-page.js` and `register-page.js`, after `saveTokens` on a successful `POST /auth/login` | `noteLoginSuccess()` → `track` | `a login failure is delivered by TelemetryService.track`; login source check | Captured |
| `user_login_failed` | `error_code` `invalid_credentials` \| `validation_error` \| `account_locked`; `attempt_bucket` `1` \| `2-5` \| `6+`. Envelope `userId` is null. | Same login handlers when `POST /auth/login` returns 401, 400, 422, or 423. A network failure is not given a login reason. | `noteLoginFailure(status)` | `login failure uses an approved reason and no credentials`; `attempt buckets advance...` | Captured |
| `user_logged_out` | `reason=user_action` for the account logout button | `session.logout()`, before `clearSession` | `noteLogout()` | `logout records the business event before the token is cleared` | Captured |
| `page_viewed` | `page` `login` \| `suppliers` \| `account` on the screens that exist. `referrer_page` is omitted. `register` is not in the enum. | `login-page.js` when signed out; `app.js` and `account-page.js` when `hasAccessToken()` is true | `noteCurrentPage()` reads `data-telemetry-page` | `page capture accepts only the approved page enum`; HTML source check | Captured for existing pages |
| `page_load_completed` | `page`, `duration_ms`, optional `connection_type` `wifi` \| `cellular` \| `ethernet` \| `unknown` | Same pages, on `window` `load` | `noteCurrentPage()` | `page capture accepts only the approved page enum` | Captured for existing pages |
| `api_request_completed` | `route_template`, `method`, `status_code` 200–299, `duration_ms` | `session.apiFetch` and the logout `POST`, one event for the caller-facing result | `noteApi()` | `apiFetch records one API event and still returns the response`; `api observations keep route templates...` | Captured |
| `api_request_failed` | Same fields plus `error_code` and `status_code` 0–599 when the code is approved | Same client paths for non-2xx and thrown `fetch` | `noteApi()` | `apiFetch records a network failure and still throws` | Captured |
| `product_validation_failed` | `error_code`, `field`, `entity`, optional `product_id`, `location_id`, `country` | None. No product or order form. | Not emitted. | No capture call in `uis/backoffice` | Not captured |
| `workflow_abandoned` | `workflow`, `step_reached`, `duration_ms`, optional `location_id`, `country` | None. The plan marks this as a proposal until the inventory UI exists. | Not emitted. | No capture call in `uis/backoffice` | Not captured |

`POST /telemetry/events` is not observed by `noteApi`, so a telemetry send cannot enqueue another telemetry event. A throw inside a telemetry hook does not change login, logout, or `apiFetch`.
