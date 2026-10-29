# Brasaland telemetry plan

Design contract for inventory telemetry and for the supplier-directory signals that already exist in this repository. Normative names, types, and allowlists are in [`event-schemas.json`](./event-schemas.json) (`schemaVersion` `1.0.0`, JSON Schema draft-07). This document does not instrument any application.

Evidence labels used below:

- **Briefing.** Required by `brasaland-BRIEFING.md` (parent of this repo). `company-BRIEFING.md` is not in the tree. The inventory application described there is not in this repository.
- **Verified.** Observed in `services/api` or `uis/backoffice`.
- **Proposal.** A design choice grounded in a briefing constraint or a verified failure path. It is not a behavior this repository already performs.

## 1. Purpose, context, scope, and principles

Brasaland is a grilled-food chain with 14 locations in Colombia and Florida. The briefing says each location depends on an inventory system for ingredients, and that operations cannot see what that system is doing. These events are the measurement floor for that system. Later course work is expected to aggregate them by location, by country, and by week for Felipe Guerrero’s operations view and Mariana Restrepo’s weekly executive report. This plan does not build those reports and does not convert currency.

**In scope**

- The six mandatory inventory metrics.
- Receiving and waste rejections required to keep those metrics trustworthy.
- Supplier create, rate change, and status change on the live supplier API, because inbound price history cannot be reconstructed from the current row.
- Auth, validation, and storage failures on that API, because a failed write must not be read as “no orders today.”

**Out of scope**

- Runtime capture, storage, dashboards, and seed loaders.
- The public website, Brasa Points, and the talent pipeline.
- UI language (Spanish/English). The briefing separates interface language from `country`.

**Principles**

1. The briefing metric table is the floor. Extra events exist only when they support a named decision.
2. Inventory facts that are not in the briefing or the repo are labeled unresolved. They are not filled in with website location names or example products.
3. `properties` is a closed allowlist. Employee names, customer data, emails, passwords, and tokens stay out.
4. Amounts stay in the location currency (`COP` or `USD`). This layer does not convert.
5. A stock change is an inbound order or an outbound/waste record. A direct edit is a rejection event, not a stock event.
6. Week, country, and location rollups are derived later from `timestamp`, `country`, and `location_id`. This schema does not add a second copy of those keys.

## 2. Mandatory metric checklist

Source: `brasaland-BRIEFING.md` section 3. All six are specified here and absent from the running API.

| Metric | In this design | Running route |
| --- | --- | --- |
| `inbound_order_created` | Yes | None |
| `outbound_order_created` | Yes | None |
| `stock_waste_registered` | Yes | None |
| `stock_threshold_triggered` | Yes | None |
| `direct_stock_edit_rejected` | Yes | None |
| `ingredient_price_variance_detected` | Yes | None |

Property floor for inventory events, in addition to the envelope: `location_id`, `country` (`CO` or `US`), `product_id`, `product_category`, `quantity`, `unit`, `currency` (`COP` or `USD`). `stock_waste_registered` also requires `reason` (`expired`, `kitchen_error`, `theft_suspected`).

The same section also names `reason` on `outbound_order_created`, and then limits the enum to waste values. The metric row defines `outbound_order_created` as consumption during preparation, and defines waste as a different event. This plan does **not** put `reason` on `outbound_order_created`. Putting the waste enum on consumption would mix the two metrics. The conflict stays open in section 10.

## 3. Catalogue

16 event types. 6 mandatory. 10 additional. 5 categories. Additional events cover 4 categories (`inventory_receiving`, `inventory_control`, `procurement`, `platform_reliability`).

| `event_type` | `entity_action` | Category | Delivery | Evidence |
| --- | --- | --- | --- | --- |
| `inbound_order_created` | `inbound_order.created` | `inventory_receiving` | stream | Briefing |
| `outbound_order_created` | `outbound_order.created` | `inventory_consumption` | stream | Briefing |
| `stock_waste_registered` | `stock_waste.registered` | `inventory_control` | stream | Briefing |
| `stock_threshold_triggered` | `stock_threshold.triggered` | `inventory_control` | stream | Briefing |
| `direct_stock_edit_rejected` | `direct_stock_edit.rejected` | `inventory_control` | stream | Briefing |
| `ingredient_price_variance_detected` | `ingredient_price_variance.detected` | `procurement` | stream | Briefing |
| `inbound_currency_mismatch_rejected` | `inbound_order.currency_mismatch_rejected` | `inventory_receiving` | stream | Proposal |
| `waste_reason_rejected` | `stock_waste.reason_rejected` | `inventory_control` | stream | Proposal |
| `supplier_rate_changed` | `supplier.rate_changed` | `procurement` | stream | Verified |
| `supplier_status_changed` | `supplier.status_changed` | `procurement` | stream | Verified |
| `supplier_created` | `supplier.created` | `procurement` | stream | Verified |
| `supplier_document_unreadable` | `supplier_document.unreadable` | `platform_reliability` | stream | Verified |
| `staff_login_failed` | `staff_session.login_failed` | `platform_reliability` | stream | Verified |
| `protected_route_unauthenticated` | `protected_route.unauthenticated` | `platform_reliability` | stream | Verified |
| `request_validation_rejected` | `request.validation_rejected` | `platform_reliability` | stream | Verified |
| `storage_unavailable` | `storage.unavailable` | `platform_reliability` | stream | Verified |

`supplier_document_unreadable` has two valid property shapes in the schema (list skip, and single-document read failure). Both use the same `event_type` and `entity_action`.

## 4. Instrumentation points

Five or more points. Inventory points are proposals. Supplier and platform points name verified code.

| ID | Workflow | Where | Events |
| --- | --- | --- | --- |
| IP-1 | Inbound receipt accepted or rejected for currency | No inventory route. Proposed beside the future inbound write | `inbound_order_created`, `inbound_currency_mismatch_rejected`, and, when the variance rule matches, `ingredient_price_variance_detected` |
| IP-2 | Preparation consumption accepted | No inventory route. Proposed beside the future consumption write | `outbound_order_created` |
| IP-3 | Waste accepted or rejected for `reason` | No inventory route. Proposed beside the future waste write | `stock_waste_registered`, `waste_reason_rejected` |
| IP-4 | On-hand quantity compared with the configured minimum after a successful inbound, consumption, or waste write | No stock balance and no minimum in TinyDB. Proposed | `stock_threshold_triggered` |
| IP-5 | Direct stock command rejected | No stock command exists. Proposed. Supplier `PATCH` is not this command | `direct_stock_edit_rejected` |
| IP-6 | Supplier create, rate change, status change | Verified: `POST /suppliers`, `PATCH /suppliers/{id}/rate`, `PATCH /suppliers/{id}/status` in `services/api/app/routers/suppliers.py`. Backoffice calls the same three in `uis/backoffice/services/suppliers.ts` | `supplier_created`, `supplier_rate_changed`, `supplier_status_changed` |
| IP-7 | Staff login and bearer check | Verified: `POST /auth/login` and `current_user_email` in `services/api/app/deps.py` | `staff_login_failed`, `protected_route_unauthenticated` |
| IP-8 | Validation, storage, and corrupt supplier documents | Verified: 422 handler in `services/api/app/main.py`, `StorageError` path, corrupt-row skip and 500 in `services/api/app/routers/suppliers.py` | `request_validation_rejected`, `storage_unavailable`, `supplier_document_unreadable` |

Emit IP-1 through IP-5 only after the inventory write has been accepted or rejected. Do not emit them from the supplier directory.

## 5. Event envelope

Every event is a JSON object with `additionalProperties: false`. Validate instances against the root `oneOf` in `event-schemas.json`. The shared envelope schema is `#/definitions/envelope`.

| Field | Required | Type | Rule |
| --- | --- | --- | --- |
| `eventId` | yes | string, UUID | Idempotency key. New UUID per emission. |
| `timestamp` | yes | string, ISO 8601 | Offset required (`Z` or `±hh:mm`). Date-only values are invalid. |
| `sessionId` | yes | UUID string or `null` | UUID when a staff session exists. `null` when it does not. Not the refresh-token `jti`. |
| `userId` | yes | opaque string or `null` | Pattern `^[A-Za-z0-9_-]{8,}$` when present. Never an email, name, phone, or address. |
| `event_type` | yes | string | Stable name from the catalogue. |
| `entity_action` | yes | string | `entity.action`, lowercase snake segments. |
| `schemaVersion` | yes | const `1.0.0` | This contract. |
| `requestId` | yes | UUID string | Correlates multiple events from one API request. |
| `properties` | yes | object | Event allowlist. Closed. |

**Identity.** Inventory events and supplier write/read-failure events require a non-null `userId` and `sessionId`, because the briefing says a stock change is traceable to a user and those supplier routes already require a bearer token. `staff_login_failed` and `protected_route_unauthenticated` require both to be `null`. `request_validation_rejected` and `storage_unavailable` allow either, because those failures also happen on public routes and on requests that die before a user is known.

**`userId` gap.** Verified accounts are keyed by email (`services/api/app/deps.py` returns the token subject, and the subject is the email). This schema rejects an email in `userId`. Implementation must allocate an opaque id before emission. That allocator is not in the repo.

Example shape (values are illustrative, not a real location or person):

```json
{
  "eventId": "6b9c2a10-7e2d-4c1a-9f0e-1a2b3c4d5e6f",
  "timestamp": "2026-10-29T22:15:00Z",
  "sessionId": "11111111-2222-4333-8444-555555555555",
  "userId": "stf_ab12cd34",
  "event_type": "inbound_order_created",
  "entity_action": "inbound_order.created",
  "schemaVersion": "1.0.0",
  "requestId": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
  "properties": {
    "location_id": "loc_co_01",
    "country": "CO",
    "supplier_id": "sup_01",
    "product_id": "prd_beef_loin",
    "product_category": "protein",
    "quantity": 12.5,
    "unit": "kg",
    "currency": "COP",
    "unit_cost": 28500
  }
}
```

The assignment screenshot also names `event_name`, `entity_id`, `source`, and `environment`. Those fields are not in this envelope. See section 10.

## 6. Event definitions

Shared inventory property types, unless a row below overrides them:

| Property | Type | Meaning |
| --- | --- | --- |
| `location_id` | string `^[A-Za-z0-9_-]{1,64}$` | Opaque location id. Website display names are not valid. |
| `country` | `CO` or `US` | Briefing country code. |
| `product_id` | same pattern as `location_id` | Opaque product id. Example ingredient names are not ids. |
| `product_category` | `protein`, `vegetable`, `sauce`, `beverage`, `packaging`, `cleaning` | Briefing categories. |
| `quantity` | number `> 0` | Movement quantity. Threshold on-hand may be `0`. |
| `unit` | string, 1–32 chars | Unit of measure. Briefing examples are `kg`, `unit`, and `liter`. The set is not closed. |
| `currency` | `COP` or `USD` | Location currency. No converted amount. |

No inventory event lists optional properties. Unknown keys are invalid.

PII for every inventory event: `properties` are business measurements, classification **not PII**. Envelope `userId` is a **sensitive identifier** (opaque). Envelope `sessionId` is a **sensitive identifier**. Exclusion: do not copy names, emails, phones, customer Brasa Points fields, or free-text notes into `properties`.

### `inbound_order_created`

- **Category:** `inventory_receiving`. **Entity / action:** `InboundOrder` / `created`. **Workflow:** IP-1.
- **Trigger:** A location’s inbound receipt is accepted.
- **Outcome:** One accepted receipt is durable in telemetry.
- **Hypothesis (briefing):** Purchasing quantity and product mix are invisible by location and supplier.
- **Decision:** Lucía Fernández consolidates purchasing and negotiates price.
- **Delivery:** Stream. A receipt has to exist before the next purchase decision. Weekly aggregation is a later read of these events, not a delayed capture.
- **Evidence:** Briefing. No route.
- **Required `properties`:** floor, plus `supplier_id` (opaque string) and `unit_cost` (number `> 0`, in `currency`).
- **Optional:** none.
- **PII:** none in `properties`. `supplier_id` is an identifier, not a contact email.

### `outbound_order_created`

- **Category:** `inventory_consumption`. **Entity / action:** `OutboundOrder` / `created`. **Workflow:** IP-2.
- **Trigger:** Ingredient consumption for dish preparation is accepted.
- **Outcome:** Consumption quantity for one product at one location is durable.
- **Hypothesis (briefing):** The consumption rate by ingredient and location is unknown.
- **Decision:** Felipe Guerrero adjusts replenishment.
- **Delivery:** Stream. The briefing’s “automatic supplier order suggestion” needs consumption before the next order cutoff, not only in a Monday report.
- **Evidence:** Briefing. No route.
- **Required `properties`:** floor only.
- **Optional:** none. `reason` is intentionally absent. See section 2.
- **PII:** none in `properties`.

### `stock_waste_registered`

- **Category:** `inventory_control`. **Entity / action:** stock waste / `registered`. **Workflow:** IP-3.
- **Trigger:** A waste record is accepted with an allowed `reason`.
- **Outcome:** Lost quantity is classifiable by reason and location.
- **Hypothesis (briefing):** The amount lost, the cause, and the location are unknown.
- **Decision:** Felipe Guerrero orders waste audits at the worst locations.
- **Delivery:** Stream. `theft_suspected` is useless if it waits for a weekly file. The same capture path is used for `expired` and `kitchen_error` so the three reasons stay comparable. The briefing does not rank the reasons.
- **Evidence:** Briefing. No route.
- **Required `properties`:** floor, plus `reason` enum `expired`, `kitchen_error`, `theft_suspected`.
- **Optional:** none.
- **PII:** none. Do not add a comment field. Free text can name a person.

### `stock_threshold_triggered`

- **Category:** `inventory_control`. **Entity / action:** stock threshold / `triggered`. **Workflow:** IP-4.
- **Trigger:** After an accepted inbound, consumption, or waste write, on-hand quantity for that product at that location is strictly below the configured minimum.
- **Outcome:** One crossing is recorded. Repeat the event only when a later write is still below the minimum after quantity has recovered to the minimum or above and then crossed again. Do not emit on every read.
- **Hypothesis (briefing):** How often a location runs short of a key ingredient is unknown.
- **Decision:** Change that product’s minimum or its replenishment frequency.
- **Delivery:** Stream. A weekly batch cannot show a shortage during service.
- **Evidence:** Briefing. No on-hand balance and no minimum are stored. `threshold_quantity` has no verified source.
- **Required `properties`:** floor, with `quantity` meaning on-hand at the crossing (`>= 0`), plus `threshold_quantity` (number `>= 0`).
- **Optional:** none.
- **PII:** none in `properties`.

### `direct_stock_edit_rejected`

- **Category:** `inventory_control`. **Entity / action:** direct stock edit / `rejected`. **Workflow:** IP-5.
- **Trigger:** A stock write that is not an accepted `InboundOrder` or waste/consumption record is rejected.
- **Outcome:** On-hand quantity is unchanged. The attempt is countable by location.
- **Hypothesis (briefing):** Staff may be bypassing traceability.
- **Decision:** Jake Morrison reinforces training or permissions where attempts cluster.
- **Delivery:** Stream. A bypass attempt should be visible the same day. Weekly counts are a later aggregate.
- **Evidence:** Briefing constraint “stock is never modified directly.” No reject path exists. There is no role model and no HTTP 403 in `services/api/app/`.
- **Required `properties`:** floor, plus `attempted_operation` (machine code `^[a-z][a-z0-9_]{0,63}$`).
- **Optional:** none.
- **PII:** do not put the user’s name in `attempted_operation`. Location is the grain the briefing asks for. The allowed operation codes are unresolved (section 10).

### `ingredient_price_variance_detected`

- **Category:** `procurement`. **Entity / action:** ingredient price variance / `detected`. **Workflow:** IP-1, only when an inbound receipt is accepted.
- **Trigger:** The receipt is accepted and `abs(unit_cost - historical_unit_cost) / historical_unit_cost > threshold_ratio`.
- **Outcome:** The receipt event and this variance event share `requestId`. No history means this event is not emitted.
- **Hypothesis (briefing):** A key ingredient can change price abnormally before anyone renegotiates.
- **Decision:** Lucía Fernández and Mariana Restrepo renegotiate or switch supplier.
- **Delivery:** Stream. The decision happens before the next purchase, not at the next weekly PDF.
- **Evidence:** Briefing. The “10%” figure is an example, not a constant in this schema. `threshold_ratio` is whatever configured value fired. Current supplier rows keep one `rate_per_unit` and overwrite it (`update_supplier_rate` in `services/api/app/database.py`), so history cannot be backfilled from TinyDB.
- **Design note:** The trigger column says “varies.” The hypothesis column says “rises.” This plan emits on absolute variance and stores a **signed** `variance_ratio` (`(unit_cost - historical_unit_cost) / historical_unit_cost`) so a later consumer can keep only increases. That choice is explicit because the two briefing sentences differ.
- **Required `properties`:** floor, plus `supplier_id`, `unit_cost`, `historical_unit_cost` (both money `> 0`), `variance_ratio` (number, may be negative), `threshold_ratio` (number `> 0`).
- **Optional:** none.
- **PII:** none in `properties`.

### `inbound_currency_mismatch_rejected`

- **Category:** `inventory_receiving`. **Entity / action:** `InboundOrder` / `currency_mismatch_rejected`. **Workflow:** IP-1.
- **Trigger:** An inbound receipt is rejected because its amount currency is not the location currency (`COP` in Colombia, `USD` in Florida).
- **Outcome:** No `inbound_order_created` for that attempt.
- **Hypothesis:** A COP amount stored as USD, or the reverse, makes purchasing totals unusable. The briefing forbids converting inside telemetry.
- **Decision:** Block the receipt and correct capture at that location.
- **Delivery:** Stream. A bad receipt should not wait until Monday.
- **Evidence:** Proposal from briefing section 6. The supplier model already rejects a Colombia/`USD` or USA/`COP` pair (`ensure_currency_matches_country`). That check is on suppliers, not on inventory receipts.
- **Required `properties`:** floor, plus `supplier_id` and `currency_submitted` (`COP` or `USD`). `currency` is the location currency. `currency_submitted` is the rejected currency. The schema rejects a payload where those two values are equal.
- **Optional:** none.
- **PII:** none in `properties`.

### `waste_reason_rejected`

- **Category:** `inventory_control`. **Entity / action:** stock waste / `reason_rejected`. **Workflow:** IP-3.
- **Trigger:** A waste submit is rejected because `reason` is missing or not one of the three allowed values.
- **Outcome:** No `stock_waste_registered` for that attempt.
- **Hypothesis:** Unclassified waste cannot be audited.
- **Decision:** Refuse the write so Felipe Guerrero’s audit stays comparable across locations.
- **Delivery:** Stream.
- **Evidence:** Proposal from the briefing’s closed `reason` enum.
- **Required `properties`:** floor, plus `reason_status` (`missing` or `unrecognized`).
- **Optional:** none.
- **PII / sanitisation:** Do not copy the submitted string. It may name a person. `unrecognized` records only that the value was outside the enum.

### `supplier_rate_changed`

- **Category:** `procurement`. **Entity / action:** `supplier` / `rate_changed`. **Workflow:** IP-6.
- **Trigger:** `PATCH /suppliers/{supplier_id}/rate` returns the updated supplier.
- **Outcome:** The previous and new `rate_per_unit` are both kept. The API itself discards the previous value.
- **Hypothesis:** Without this event, `ingredient_price_variance_detected` has no history, because the directory stores one current rate.
- **Decision:** Lucía Fernández can see the directory price that will be compared with the next inbound unit cost. Do not treat `rate_per_unit` as a product `unit_cost`. One supplier has one rate for every category on the row.
- **Delivery:** Stream. The next inbound comparison needs the new baseline immediately.
- **Evidence:** Verified route and `update_supplier_rate`.
- **Required `properties`:** `supplier_id` (decimal string of the TinyDB integer id), `country` (`Colombia` or `USA`), `currency`, `categories` (one or more directory categories), `previous_rate`, `new_rate` (both `> 0`).
- **Optional:** none.
- **Emitter rule:** If `previous_rate` and `new_rate` are equal, do not emit. The schema cannot express numeric inequality. The API accepts a patch that repeats the current rate. That patch is not a price change.
- **PII / sanitisation:** Do not copy `contact_email` or `notes`.

Directory categories, verified in `services/api/app/models.py`: `carne`, `verduras_y_hortalizas`, `salsas_y_condimentos`, `bebidas`, `packaging`, `productos_limpieza`, `lacteos`, `carbon_y_combustible`.

### `supplier_status_changed`

- **Category:** `procurement`. **Entity / action:** `supplier` / `status_changed`. **Workflow:** IP-6.
- **Trigger:** `PATCH /suppliers/{supplier_id}/status` succeeds.
- **Outcome:** The previous and new status are durable.
- **Hypothesis:** A suspended supplier can still be treated as available for the next inbound suggestion if only the current row is checked too late, or if the change is missed.
- **Decision:** Do not suggest a `suspended` supplier for replenishment. The seed marks Limpiahogar Profesional suspended for delivery non-compliance. That note is context for the status value. Do not copy `notes` into the event.
- **Delivery:** Stream.
- **Evidence:** Verified route. Status enum `active` or `suspended`.
- **Required `properties`:** `supplier_id` (decimal TinyDB id), `country` (`Colombia` or `USA`), `previous_status`, `new_status`. The schema rejects a pair where those two statuses are equal.
- **Optional:** none.
- **PII:** none. Omit email and notes.

### `supplier_created`

- **Category:** `procurement`. **Entity / action:** `supplier` / `created`. **Workflow:** IP-6.
- **Trigger:** `POST /suppliers` returns 201.
- **Outcome:** The new supplier id is known before any inbound receipt references it.
- **Hypothesis:** Inbound receipts need a supplier that already exists in the directory Lucía uses.
- **Decision:** A new supplier may be used on a later inbound order. A `suspended` create is visible immediately.
- **Delivery:** Stream.
- **Evidence:** Verified route. Backoffice create form calls it.
- **Required `properties`:** `supplier_id` (decimal TinyDB id), `country` (`Colombia` or `USA`), `currency`, `categories`, `status`.
- **Optional:** none.
- **PII / sanitisation:** The allowlist omits `name`, `contact_email`, and `notes`. A supplier trade name is not customer data, but `SupplierCreate` places `contact_email` beside `name`. Copying the create body would leak the email. The id, country, currency, categories, and status are enough for the decision.

### `supplier_document_unreadable`

- **Category:** `platform_reliability`. **Entity / action:** supplier document / `unreadable`. **Workflow:** IP-8.
- **Trigger:** `GET /suppliers` skips a corrupt document, or `GET` / `PATCH` / `DELETE` on one id returns 500 `Stored supplier data is invalid`.
- **Outcome:** The skip is visible. A 200 list is not proof that every supplier was returned.
- **Hypothesis:** Lucía’s list can be short while the API still returns 200, because corrupt rows are skipped and only logged.
- **Decision:** Repair the document before using that supplier on an inbound order.
- **Delivery:** Stream.
- **Evidence:** Verified in `list_suppliers` (skip and warning) and `_stored_data_invalid` (HTTP 500).
- **Shape A, required:** `supplier_id`, `outcome` = `skipped_on_list`. `http_status` is forbidden on this shape.
- **Shape B, required:** `supplier_id`, `outcome` = `read_failed`, `http_status` = `500`.
- **Optional:** none inside each shape.
- **PII:** do not include the corrupt document body. It can contain `contact_email`.
- **Identity:** non-null `userId` and `sessionId`. These routes require a bearer token.

### `staff_login_failed`

- **Category:** `platform_reliability`. **Entity / action:** staff session / `login_failed`. **Workflow:** IP-7.
- **Trigger:** `POST /auth/login` returns 401 `Incorrect email or password`.
- **Outcome:** A failed authentication is countable without storing who was attempted.
- **Hypothesis:** Repeated failures at the staff desk are either a shared-terminal problem or guessing. The current API returns the same 401 for an unknown email and a wrong password (`authenticate_user`).
- **Decision:** Investigate a spike. Do not build an employee-level lockout from this event. It has no user key, on purpose.
- **Delivery:** Stream the event. Alert on a spike, not on every single failure.
- **Evidence:** Verified `services/api/app/routers/auth.py`.
- **Required `properties`:** `outcome` = `invalid_credentials`.
- **Optional:** none.
- **Identity:** `userId` and `sessionId` are `null`.
- **PII / sanitisation:** Do not copy email, password, or the raw `detail` string.

### `protected_route_unauthenticated`

- **Category:** `platform_reliability`. **Entity / action:** protected route / `unauthenticated`. **Workflow:** IP-7.
- **Trigger:** A route that uses `current_user_email` returns 401 before the handler runs.
- **Outcome:** The rejection reason is one of the three verified messages.
- **Hypothesis:** Calls without a usable access token are a broken staff session or a client sending no credentials. Today that includes every `/suppliers` method.
- **Decision:** Separate “the desk is not signed in” from “a stock write was rejected by policy.” This event is not `direct_stock_edit_rejected`.
- **Delivery:** Stream. Alert on a spike.
- **Evidence:** Verified details from `services/api/app/deps.py` and `services/api/app/security.py`: `Not authenticated`, `Session expired`, `Invalid token`.
- **Required `properties`:** `route`, `status_code` = `401`, `detail` (that enum).
- **Optional:** none.
- **Identity:** `userId` and `sessionId` are `null`.
- **PII / sanitisation:** Do not copy the bearer token or the email inside it.

### `request_validation_rejected`

- **Category:** `platform_reliability`. **Entity / action:** request / `validation_rejected`. **Workflow:** IP-8.
- **Trigger:** The API returns 422 from `RequestValidationError`.
- **Outcome:** The attempt did not change stored data. Only the error count is kept.
- **Hypothesis:** Currency/country mismatches, non-positive rates, and extra fields already fail supplier writes. Those rejects are invisible if the client only shows a form error.
- **Decision:** See whether a location’s client is systematically sending invalid supplier or, later, inventory payloads.
- **Delivery:** Stream.
- **Evidence:** Verified handler in `services/api/app/main.py`. Models reject `rate_per_unit <= 0`, mismatched currency, and client `id` / `updated_at`.
- **Required `properties`:** `route`, `status_code` = `422`, `error_count` (integer `>= 1`).
- **Optional:** none.
- **Identity:** `userId` and `sessionId` may be `null` or set.
- **PII / sanitisation:** Do not copy `detail[]`, field paths, or submitted values. A register or supplier body can contain an email.

### `storage_unavailable`

- **Category:** `platform_reliability`. **Entity / action:** storage / `unavailable`. **Workflow:** IP-8.
- **Trigger:** A `StorageError` becomes HTTP 500 `Storage unavailable`.
- **Outcome:** The write or read did not complete. TinyDB paths raise this on `OSError` and on unreadable JSON (`services/api/app/database.py`).
- **Hypothesis:** A quiet location may be a disk or file failure rather than a true absence of orders.
- **Decision:** Treat the interval as unknown. Do not impute zero inbound or zero waste for that period.
- **Delivery:** Stream.
- **Evidence:** Verified error string `Storage unavailable` in `services/api/app/errors.py`.
- **Required `properties`:** `route`, `status_code` = `500`, `detail` = `Storage unavailable`.
- **Optional:** none.
- **Identity:** `userId` and `sessionId` may be `null` or set.
- **PII:** Do not include filesystem paths. The API already hides them from the client.

## 7. Delivery strategy

**Class.** All 16 events are **stream** at capture. Batch capture would recreate the delay the company already has: leadership waits on a weekly file. Weekly and country rollups are downstream reads. They are not a second way to deliver the event.

**Urgency.**

| Need | Events | Why stream |
| --- | --- | --- |
| Same-day shortage | `stock_threshold_triggered` | Service is already open when stock crosses the minimum |
| Same-day traceability breach | `direct_stock_edit_rejected` | Training follows the locations where attempts cluster |
| Next purchase | `inbound_order_created`, `outbound_order_created`, `ingredient_price_variance_detected`, `supplier_rate_changed`, `supplier_status_changed`, `supplier_created` | Price and replenishment decisions happen before the next order |
| Trust of the waste metric | `stock_waste_registered`, `waste_reason_rejected`, `inbound_currency_mismatch_rejected` | A rejected or unclassified write must not be counted as success |
| Do not misread downtime | `storage_unavailable`, `supplier_document_unreadable`, `request_validation_rejected`, `staff_login_failed`, `protected_route_unauthenticated` | A 500 or a 401 is not “no activity” |

**Frequency.** No production rate is evidenced. The briefing’s “15–20 orders” figures are a future seed minimum, not a measured volume. Do not size capacity from them.

**Failure handling (proposal).**

- Emit only after the business outcome is known.
- Publish at-least-once.
- Consumers dedupe on `eventId`.
- Retry up to 5 times with exponential backoff. That count is a proposal, not a measured requirement.
- Then dead-letter the payload, still keyed by `eventId`.
- A telemetry failure does not roll back a business write that already succeeded, and does not turn a rejection into a success.
- Do not log the raw `properties` plus headers in the dead letter if that copy would add a token or an email. The allowlist is the whole payload.

No vendor, broker, or region is chosen here.

## 8. Risks, limitations, and exclusions

**Not captured, and why**

| Excluded | Reason |
| --- | --- |
| Employee name, email, phone, address | Briefing forbids employee names in `properties`. The live user key is an email, so it is excluded from `userId` too. |
| Customer Brasa Points fields | Website form collects them and does not submit them to an API (`uis/website/components/BrasaPointsForm.tsx`). Inventory events are not customer events. |
| Passwords, access tokens, refresh tokens, reset tokens, `jti` | Credentials. `sessionId` is a separate UUID. |
| `contact_email`, `notes`, supplier document body | Present on the supplier model. They can identify a person or leak a corrupt payload. |
| Supplier trade `name` | Omitted so create/update bodies are not copied wholesale. |
| UI language | Briefing: do not mix language with `country`. |
| Converted currency and FX rate | Briefing: conversion is a later reporting job. |
| `city` | Section 2 of the briefing mentions city. The property floor does not. There is no location registry. Free-text city would invite display names. |
| Website restaurant names as `location_id` | `CONTEXT.md` lists 14 display names. They contain spaces and fail the id pattern. They are not an id scheme. |
| `DELETE /suppliers/{id}` | The route exists. The backoffice does not call it. No business decision for a delete event was stated. |
| `GET /health` | No decision. |
| Talent pipeline events | Different application. |
| Page views and clicks | No inventory decision. |

**Limitations**

- Inventory routes, products, stock balances, minimums, and price history are not in this repo. IP-1 through IP-5 cannot be switched on by editing this file.
- Any authenticated staff token can create, reprice, suspend, or delete a supplier. A 401 is not an authorization policy for stock.
- Directory `country` is `Colombia` or `USA`. Inventory `country` is `CO` or `US`. This plan does not translate one into the other.
- Directory categories and inventory categories are different lists. `lacteos` and `carbon_y_combustible` have no inventory enum value. Do not map `carne` to `protein` inside telemetry.
- The checked-in seed has 15 suppliers. The briefing says about 20.
- Week boundaries have no stated timezone. Do not assume Medellín or Miami when aggregating `timestamp`.
- `unit` is open text with a length cap. That cap is a leakage limit, not a business unit catalogue.

## 9. Traceability

| Requirement | Event | Measurable outcome | Decision |
| --- | --- | --- | --- |
| Purchases by location and supplier | `inbound_order_created` | Sum of `quantity` and `unit_cost` by `location_id`, `supplier_id`, `product_id`, `country`, week | Lucía consolidates purchasing |
| Consumption rate | `outbound_order_created` | Sum of `quantity` by `product_id` and `location_id` over time | Felipe adjusts replenishment |
| Waste by cause and location | `stock_waste_registered` | Sum of `quantity` by `reason` and `location_id` | Felipe orders audits |
| Shortages | `stock_threshold_triggered` | Count of crossings by `product_id` and `location_id` | Change minimum or replenishment frequency |
| Traceability bypass | `direct_stock_edit_rejected` | Count by `location_id` | Jake targets training |
| Abnormal unit cost | `ingredient_price_variance_detected` | Events where the absolute ratio exceeds the stored `threshold_ratio` | Lucía and Mariana renegotiate or switch supplier |
| Local currency only | `inbound_currency_mismatch_rejected` | Count of rejects by `location_id` | Fix capture. Do not convert |
| Classifiable waste | `waste_reason_rejected` | Count of `missing` vs `unrecognized` | Keep the waste metric comparable |
| Price history the API does not store | `supplier_rate_changed` | `previous_rate` and `new_rate` by `supplier_id` | Baseline for the next variance check |
| Suspended suppliers | `supplier_status_changed` | Latest `new_status` by `supplier_id` | Keep suspended suppliers out of replenishment |
| Directory gains a supplier | `supplier_created` | New `supplier_id` values | Know who can appear on a later receipt |
| Silent list gaps | `supplier_document_unreadable` | Count of `skipped_on_list` and `read_failed` | Repair before using the supplier |
| Failed sign-in | `staff_login_failed` | Count of `invalid_credentials` over time | Investigate spikes without identifying the person |
| Missing bearer token | `protected_route_unauthenticated` | Count by `detail` and `route` | Separate session failure from a policy reject |
| Invalid payload | `request_validation_rejected` | `error_count` by `route` | Find a client that is systematically invalid |
| Store down | `storage_unavailable` | Count by `route` over time | Do not impute zero activity |

Future aggregates the briefing already asks for use `location_id`, `country`, and the week of `timestamp`. They are not new events.

## 10. Unresolved issues

1. **`reason` on `outbound_order_created`.** The property sentence names that event. The metric row and the waste enum do not describe a consumption reason. This schema omits `reason` there.
2. **Variance direction.** Trigger text says “varies.” Hypothesis text says “rises.” Section 6 chooses absolute variance and keeps a signed ratio.
3. **`threshold_ratio` and stock minimums** are not configured anywhere. `10%` is an example.
4. **`attempted_operation` codes** have no catalogue.
5. **Opaque `userId`** is required and not implemented. Email is the live subject.
6. **Country codes and category lists** differ between the briefing and `services/api/app/models.py`. No mapping is defined.
7. **`location_id` / `product_id` formats** are patterns only. The 14 names in `CONTEXT.md` are display labels.
8. **Supplier id types.** Inventory `supplier_id` is an opaque string. Directory events use the decimal TinyDB id. They are not established as the same identifier.
9. **Envelope names.** This phase requires `eventId`, `timestamp`, `sessionId`, `userId`, `event_type`, `entity_action`, `schemaVersion`, `requestId`, and `properties`. The assignment screenshot also uses `event_name`, `entity_id`, `source`, and `environment`. Those screenshot fields are absent here.
10. **Filename.** This phase asks for `docs/telemetry/event-schemas.json`. The assignment screenshot asks for `docs/telemetry/event-schema.json`. The singular file was not created.
11. **Supplier count.** Seed files contain 15 suppliers. The briefing says about 20.
12. **Week timezone** is unspecified.
13. **`DELETE /suppliers/{id}`** has no telemetry event.
14. **Retry count of 5** is a proposal.
