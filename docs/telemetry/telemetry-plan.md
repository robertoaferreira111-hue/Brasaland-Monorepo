# Brasaland Telemetry Plan

**Company:** Brasaland — grilled-food restaurant chain (14 locations, Colombia & Florida)  
**Domain:** Inventory management (ingredients and supplies per location)  
**Schema version:** `1.0.0`  
**Companion schema:** [`event-schemas.json`](./event-schemas.json)  
**Authoritative briefing:** [`company-BRIEFING/brasaland-BRIEFING.md`](../../company-BRIEFING/brasaland-BRIEFING.md)  
**Assignment source:** [`.project_instructions/Designing your company's telemetry plan.png`](../../.project_instructions/Designing%20your%20company's%20telemetry%20plan.png)

This document is **design-only**. It does not instrument the application. It defines what to capture, why, property allowlists, privacy rules, and stream-versus-batch delivery so another developer can implement without clarifying basic event contracts.

---

## 1. Purpose, context, scope, and design principles

### Purpose

Give operations (Felipe), procurement (Lucía), and executives (Mariana) trustworthy signals about purchasing, consumption, waste, stock risk, control bypass attempts, and abnormal ingredient prices — aggregated later by location, country, and week.

### Business context

Brasaland’s inventory system controls meats, vegetables, sauces, beverages, packaging, and cleaning supplies across 14 locations. Stock must never be edited directly: every change is traceable through inbound or outbound orders linked to a user ([`brasaland-BRIEFING.md`](../../company-BRIEFING/brasaland-BRIEFING.md) §6).

### Scope

| In scope | Out of scope (this plan) |
| --- | --- |
| Mandatory inventory metrics from the company briefing | Runtime SDKs, storage pipelines, dashboards |
| Additional auth, navigation, performance, and error events grounded in the monorepo’s staff API/UI | Loyalty-website language telemetry mixed with `country` |
| Event envelope, allowlists, PII rules, delivery strategy | Currency conversion at the telemetry layer |

### Evidence posture

| Claim type | How it is labeled |
| --- | --- |
| Mandatory metrics and inventory entities | From [`brasaland-BRIEFING.md`](../../company-BRIEFING/brasaland-BRIEFING.md) — required floor of this plan |
| Auth / supplier-directory / backoffice behaviors | Verified in `services/api` and `uis/backoffice` (Phase 1) |
| Inventory HTTP routes for Product / InboundOrder / OutboundOrder | **Not present** in the current monorepo codebase — mandatory events are still designed as the briefing requires; implementation targets the inventory system described there |

### Design principles

1. Every event answers a hypothesis and enables a decision (assignment golden rule).
2. `event_type` uses `entity_action` naming (e.g. `inbound_order_created`).
3. Envelope fields are fixed; `properties` are closed allowlists (`additionalProperties: false`).
4. No employee names, customer data, emails, passwords, or tokens in `properties`.
5. Amounts stay in local currency (`COP` / `USD`); no conversion in telemetry.
6. `country` is `CO` | `US` and is independent of UI language.

---

## 2. Mandatory metrics checklist (company briefing)

Source: [`company-BRIEFING/brasaland-BRIEFING.md`](../../company-BRIEFING/brasaland-BRIEFING.md) §3.

| # | `event_type` | Present in this plan | Present in `event-schemas.json` |
| --- | --- | --- | --- |
| 1 | `inbound_order_created` | Yes | Yes |
| 2 | `outbound_order_created` | Yes | Yes |
| 3 | `stock_waste_registered` | Yes | Yes |
| 4 | `stock_threshold_triggered` | Yes | Yes |
| 5 | `direct_stock_edit_rejected` | Yes | Yes |
| 6 | `ingredient_price_variance_detected` | Yes | Yes |

**Minimum inventory `properties` (briefing):** `location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit`, `currency`, plus `reason` on waste (and available on outbound where applicable).  
**Prohibited in properties:** employee names, customer data.

---

## 3. Inventory entities (briefing)

| Entity | Meaning at Brasaland |
| --- | --- |
| `Product` | Ingredient/supply (e.g. beef loin, house sauce) with unit and category |
| `InboundOrder` | Goods received from a supplier at a location |
| `OutboundOrder` | Consumption in dish prep, or recorded waste |
| `location` | One of 14 sites; `country` = `CO` \| `US` |
| `supplier` | ~20 suppliers, different per country |

---

## 4. Instrumentation points (≥5)

Inventory workflow (briefing + assignment examples):

```text
Operator session
  → Create inbound order (goods received)
  → Create outbound order (consumption)
  → Register waste (outbound waste path)
  → Stock drops below minimum → threshold alert
  → Attempt direct stock edit → rejected
  → Inbound unit cost vs history → price variance
  → Validations fail on product/order fields
  → Navigate sections / abandon mid-flow
  → Login success / failure
```

| # | Instrumentation point | Primary event(s) | Class |
| --- | --- | --- | --- |
| 1 | Inbound goods registered | `inbound_order_created` | Mandatory |
| 2 | Consumption registered | `outbound_order_created` | Mandatory |
| 3 | Waste registered | `stock_waste_registered` | Mandatory |
| 4 | Stock below minimum | `stock_threshold_triggered` | Mandatory |
| 5 | Direct stock edit blocked | `direct_stock_edit_rejected` | Mandatory |
| 6 | Abnormal inbound unit cost | `ingredient_price_variance_detected` | Mandatory |
| 7 | Product/order validation failure | `product_validation_failed` | Additional |
| 8 | Failed / successful login | `user_login_failed`, `user_logged_in` | Additional |
| 9 | Section navigation / abandonment | `page_viewed`, `workflow_abandoned` | Additional |
| 10 | API latency / failures | `api_request_completed`, `api_request_failed` | Additional |

---

## 5. Event envelope

Every emitted event MUST include:

| Field | Type | Description |
| --- | --- | --- |
| `eventId` | string (UUID) | Unique id per emission |
| `timestamp` | string (ISO 8601 UTC) | When the event occurred |
| `sessionId` | string (UUID) | Opaque session id |
| `userId` | string \| null | Opaque staff user id; `null` only for pre-auth events |
| `event_type` | string | Stable name in `entity_action` form |
| `entity_action` | string | Same `entity_action` value as `event_type` (explicit naming field required by assignment Phase 2) |
| `schemaVersion` | string | Semver; current `1.0.0` |
| `requestId` | string (UUID) | Correlates UI action and API request |
| `properties` | object | Event-specific allowlisted payload only |

Machine-readable definition: [`event-schemas.json`](./event-schemas.json) (JSON Schema **draft-07**). Event contracts live under `x-events`; shared types under `definitions`; catalog metadata under `x-schemaVersion` and `x-prohibitedProperties`.

---

## 6. Event catalogue

### 6.1 Mandatory inventory events

#### `inbound_order_created`

| | |
| --- | --- |
| **Category** | business / inventory |
| **Entity / action / workflow** | `inbound_order` / `created` / receive goods at location |
| **Trigger** | Location registers arrival of goods from a supplier |
| **Observable outcome** | Inbound order persisted; stock increases via order path |
| **Hypothesis** | We capture `inbound_order_created` because we need to know how much and what is being purchased, by location and supplier, which allows us to make the decision to consolidate purchasing across locations to negotiate better prices (Lucía). |
| **Decision** | Consolidate purchasing / negotiate supplier prices |
| **Delivery** | **stream** — purchasing volume feeds near-term ops and price negotiation |
| **Required properties** | `location_id` (string), `country` (`CO`\|`US`), `product_id` (string), `product_category` (enum), `quantity` (number > 0), `unit` (enum), `currency` (`COP`\|`USD`), `supplier_id` (string), `unit_cost` (number > 0), `inbound_order_id` (string) |
| **Optional properties** | none |
| **PII / sensitive** | None expected. No employee or customer fields. |
| **Exclusion / sanitisation** | Omit supplier contact email, free-text notes, employee names. |

#### `outbound_order_created`

| | |
| --- | --- |
| **Category** | business / inventory |
| **Entity / action / workflow** | `outbound_order` / `created` / dish-prep consumption |
| **Trigger** | Location registers ingredient consumption in dish preparation |
| **Observable outcome** | Outbound order persisted; stock decreases via order path |
| **Hypothesis** | We capture `outbound_order_created` because we need to know which ingredients are consumed most, and at what rate, by location, which allows us to make the decision to adjust the automatic supplier order suggestion (Felipe). |
| **Decision** | Adjust auto replenishment suggestions |
| **Delivery** | **stream** — consumption rate drives replenishment |
| **Required properties** | `location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit`, `currency`, `outbound_order_id`, `reason` (`prep_consumption`) |
| **Optional properties** | none |
| **PII / sensitive** | None. |
| **Exclusion / sanitisation** | No dish/customer ticket PII; no employee names. |

#### `stock_waste_registered`

| | |
| --- | --- |
| **Category** | business / inventory |
| **Entity / action / workflow** | `stock_waste` / `registered` / waste recording |
| **Trigger** | Location registers waste (expired, kitchen error, or loss/theft) |
| **Observable outcome** | Waste recorded (outbound waste path); stock reduced with reason |
| **Hypothesis** | We capture `stock_waste_registered` because we need to know how much product is lost, why, and at which location, which allows us to make the decision to prioritise waste audits at the worst-performing locations (Felipe). |
| **Decision** | Prioritise waste audits |
| **Delivery** | **stream** — waste spikes need timely ops attention |
| **Required properties** | `location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit`, `currency`, `outbound_order_id`, `reason` (`expired`\|`kitchen_error`\|`theft_suspected`) |
| **Optional properties** | none |
| **PII / sensitive** | `theft_suspected` is operational, not personal identity. Still omit employee names. |
| **Exclusion / sanitisation** | No accused-person identifiers; reason enum only. |

#### `stock_threshold_triggered`

| | |
| --- | --- |
| **Category** | business / inventory |
| **Entity / action / workflow** | `stock` / `threshold_triggered` / min-stock monitoring |
| **Trigger** | Product stock at a location falls below configured minimum |
| **Observable outcome** | Threshold alert condition detected |
| **Hypothesis** | We capture `stock_threshold_triggered` because we need to know how often a location runs short of a key ingredient, which allows us to make the decision to adjust the minimum threshold or replenishment frequency for that product. |
| **Decision** | Adjust min threshold or replenishment cadence |
| **Delivery** | **stream** — stockouts are time-sensitive |
| **Required properties** | `location_id`, `country`, `product_id`, `product_category`, `quantity` (current on-hand), `unit`, `currency`, `minimum_quantity` (number > 0) |
| **Optional properties** | none |
| **PII / sensitive** | None. |
| **Exclusion / sanitisation** | No free-text alert messages that might embed staff names. |

#### `direct_stock_edit_rejected`

| | |
| --- | --- |
| **Category** | business / inventory + security/controls |
| **Entity / action / workflow** | `stock` / `edit_rejected` / bypass attempt |
| **Trigger** | User attempts to modify stock directly (outside an order) and the system rejects it |
| **Observable outcome** | Request rejected; stock unchanged |
| **Hypothesis** | We capture `direct_stock_edit_rejected` because we need to know if staff are attempting to bypass traceability controls, which allows us to make the decision to reinforce training or permissions at the locations where this happens most (Jake). |
| **Decision** | Training / permission hardening by location |
| **Delivery** | **stream** — control bypass is a security/ops signal |
| **Required properties** | `location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit`, `currency`, `rejection_code` (`direct_edit_forbidden`) |
| **Optional properties** | none |
| **PII / sensitive** | `userId` stays in envelope (opaque). No names in properties. |
| **Exclusion / sanitisation** | Do not store attempted free-text justifications. |

#### `ingredient_price_variance_detected`

| | |
| --- | --- |
| **Category** | business / inventory + procurement |
| **Entity / action / workflow** | `ingredient_price` / `variance_detected` / inbound cost check |
| **Trigger** | Unit cost on an inbound order varies more than the configured threshold (e.g. 10%) from historical value for that product/supplier |
| **Observable outcome** | Variance flagged against history |
| **Hypothesis** | We capture `ingredient_price_variance_detected` because we need to know when a key ingredient rises in price abnormally, which allows us to make the decision to alert Lucía and Mariana to renegotiate or find an alternate supplier. |
| **Decision** | Renegotiate or switch supplier |
| **Delivery** | **stream** — abnormal price needs procurement attention |
| **Required properties** | `location_id`, `country`, `product_id`, `product_category`, `quantity`, `unit`, `currency`, `supplier_id`, `unit_cost`, `historical_unit_cost`, `variance_pct`, `variance_threshold_pct`, `inbound_order_id` |
| **Optional properties** | none |
| **PII / sensitive** | None. |
| **Exclusion / sanitisation** | Numeric costs only; no contract free text. |

---

### 6.2 Additional events (≥8, ≥3 categories)

#### `product_validation_failed` — errors / business

| | |
| --- | --- |
| **Trigger** | Create/update of product or order fields fails validation |
| **Hypothesis** | We capture `product_validation_failed` because we need to know which products and fields accumulate the most validation errors, which allows us to make the decision to fix UX defaults or clarify required units/categories. |
| **Decision** | Improve forms / validation messaging |
| **Delivery** | **stream** — error quality affects daily ops entry |
| **Required properties** | `error_code` (string enum), `field` (string enum), `entity` (`product`\|`inbound_order`\|`outbound_order`) |
| **Optional properties** | `product_id`, `location_id`, `country` |
| **PII** | None; never include raw invalid email/name payloads |

#### `user_logged_in` — authentication

| | |
| --- | --- |
| **Trigger** | Successful staff authentication (verified pattern: `POST /auth/login` in `services/api`) |
| **Hypothesis** | We capture `user_logged_in` because we need to know successful session starts by day, which allows us to make the decision how to size concurrent operator capacity and detect abnormal login spikes. |
| **Decision** | Capacity planning / anomaly review |
| **Delivery** | **stream** |
| **Required properties** | `auth_method` (`password`) |
| **Optional properties** | none |
| **PII** | Opaque `userId` in envelope only; no email in properties |

#### `user_login_failed` — authentication

| | |
| --- | --- |
| **Trigger** | Login rejected (verified: 401 incorrect credentials on `/auth/login`) |
| **Hypothesis** | We capture `user_login_failed` because we need to know how many failed login attempts occur per day, which allows us to make the decision when to enable rate limits or investigate credential stuffing. |
| **Decision** | Rate limits / security follow-up |
| **Delivery** | **stream** |
| **Required properties** | `error_code` (`invalid_credentials`\|`validation_error`\|`account_locked`), `attempt_bucket` (`1`\|`2-5`\|`6+`) |
| **Optional properties** | none |
| **PII** | `userId` null; never store attempted email/password |

#### `user_logged_out` — authentication

| | |
| --- | --- |
| **Trigger** | Explicit logout or refresh revocation (verified: `POST /auth/logout`) |
| **Hypothesis** | We capture `user_logged_out` because we need to know how sessions end, which allows us to make the decision whether idle timeouts match operator workflows. |
| **Decision** | Session-timeout policy |
| **Delivery** | **batch** — useful for aggregates, not paging |
| **Required properties** | `reason` (`user_action`\|`token_revoked`\|`session_expired`) |
| **PII** | Opaque `userId` only |

#### `page_viewed` — navigation

| | |
| --- | --- |
| **Trigger** | Operator opens a named inventory/ops UI section |
| **Hypothesis** | We capture `page_viewed` because we need to know which sections operators visit most, which allows us to make the decision which screens deserve clearer IA or shortcuts. |
| **Decision** | Navigation / IA priorities |
| **Delivery** | **batch** — high volume analytics |
| **Required properties** | `page` (enum: `login`, `inbound_orders`, `outbound_orders`, `stock`, `products`, `suppliers`, `account`) |
| **Optional properties** | `referrer_page` |
| **PII** | Page enums only; no full URLs with tokens |

#### `workflow_abandoned` — navigation / business

| | |
| --- | --- |
| **Trigger** | Inbound/outbound create flow started then left before successful submit (UI-detectable; **proposed** instrumentation on form lifecycle) |
| **Hypothesis** | We capture `workflow_abandoned` because we need to know whether flows are abandoned halfway through, which allows us to make the decision to simplify forms or save drafts. |
| **Decision** | Form UX / draft support |
| **Delivery** | **batch** |
| **Required properties** | `workflow` (`inbound_order_create`\|`outbound_order_create`\|`waste_register`), `step_reached` (string enum), `duration_ms` (number ≥ 0) |
| **Optional properties** | `location_id`, `country` |
| **PII** | None |
| **Evidence note** | Labeled **proposal** — abandonment is a product intent from the assignment tech-lead questions; exact step enum must match the UI when built. |

#### `api_request_completed` — performance

| | |
| --- | --- |
| **Trigger** | Inventory/API request returns 2xx |
| **Hypothesis** | We capture `api_request_completed` because we need to know API response times by route, which allows us to make the decision which endpoints to optimize before peak service hours. |
| **Decision** | Performance investment priority |
| **Delivery** | **batch** |
| **Required properties** | `route_template` (string), `method` (enum), `status_code` (200–299), `duration_ms` (number ≥ 0) |
| **PII** | Route templates only; no query strings with emails |

#### `api_request_failed` — errors / performance

| | |
| --- | --- |
| **Trigger** | Inventory/API request returns 4xx/5xx or transport failure |
| **Hypothesis** | We capture `api_request_failed` because we need to know operational failure rates by route, which allows us to make the decision when to page on-call versus fix a client bug. |
| **Decision** | Incident response vs client fix |
| **Delivery** | **stream** — failures are urgent |
| **Required properties** | `route_template`, `method`, `status_code` (400–599 or `0` for network), `error_code` (enum), `duration_ms` |
| **PII** | No response bodies or stack traces with secrets |

#### `page_load_completed` — performance

| | |
| --- | --- |
| **Trigger** | Ops UI page reaches interactive load |
| **Hypothesis** | We capture `page_load_completed` because we need to know page-load latency by section, which allows us to make the decision whether frontend performance work is justified. |
| **Decision** | FE performance backlog |
| **Delivery** | **batch** |
| **Required properties** | `page` (same enum as `page_viewed`), `duration_ms` |
| **Optional properties** | `connection_type` (`wifi`\|`cellular`\|`ethernet`\|`unknown`) |
| **PII** | None |

---

## 7. Catalogue summary

| Class | Count | Events |
| --- | --- | --- |
| **Mandatory** (briefing) | 6 | `inbound_order_created`, `outbound_order_created`, `stock_waste_registered`, `stock_threshold_triggered`, `direct_stock_edit_rejected`, `ingredient_price_variance_detected` |
| **Additional** | 9 | `product_validation_failed`, `user_logged_in`, `user_login_failed`, `user_logged_out`, `page_viewed`, `workflow_abandoned`, `api_request_completed`, `api_request_failed`, `page_load_completed` |

**Total events:** 15  
**Categories covered:** business/inventory, authentication, navigation, performance, errors

---

## 8. Delivery strategy

### Stream versus batch

| Mode | Events | Business urgency |
| --- | --- | --- |
| **stream** (seconds) | All 6 mandatory inventory events; `product_validation_failed`; `user_logged_in`; `user_login_failed`; `api_request_failed` | Stock risk, waste, price shocks, control bypass, auth abuse, and API outages need near-real-time visibility |
| **batch** (periodic flush) | `user_logged_out`; `page_viewed`; `workflow_abandoned`; `api_request_completed`; `page_load_completed` | Analytics and UX aggregates; minute-level delay is acceptable |

### Frequency, failure handling, retries

| Topic | Decision |
| --- | --- |
| Client buffering | Batch events may buffer locally and flush on interval, page hide, or N events |
| Stream failure | Retry with exponential backoff; drop after max attempts and emit a local counter (not PII) |
| Exactly-once | Not required at capture; consumers must be idempotent on `eventId` |
| Bounce / poison | Invalid schema events are rejected by the collector and counted as `schema_reject` operational metrics (out of band) — do not re-queue forever |
| Clock skew | Prefer server receipt time for storage indexes; keep client `timestamp` for UX timing analysis |

---

## 9. Risks, limitations, exclusions

| Item | Reason |
| --- | --- |
| No employee names or customer data in properties | Briefing §3 and privacy policy |
| No passwords, JWTs, refresh tokens, Authorization headers | Credential leakage risk (verified auth uses JWTs in backoffice `localStorage`) |
| No currency conversion in telemetry | Briefing §6 — executive pipeline owns FX |
| No UI-language events mixed into `country` | Briefing §6 |
| Keystroke-level analytics | Cost/noise; not required |
| Exact geolocation / device fingerprinting | Disproportionate privacy risk |
| Current monorepo lacks Product/Inbound/Outbound HTTP APIs | **Limitation:** mandatory events are designed from the briefing; implementers must wire them when those inventory routes exist. Supplier-directory APIs remain a separate verified surface (`services/api`) and are not substitutes for mandatory inventory metrics. |
| `workflow_abandoned` step model | **Proposal** until UI steps are finalized |

---

## 10. Traceability matrix

| Requirement / question | Event(s) | Measurable outcome | Decision supported |
| --- | --- | --- | --- |
| Briefing: purchasing by location/supplier | `inbound_order_created` | Counts/qty by location, country, supplier, week | Consolidate purchasing (Lucía) |
| Briefing: consumption rate | `outbound_order_created` | Consumption by product/location | Auto order suggestions (Felipe) |
| Briefing: waste why/where | `stock_waste_registered` | Waste qty by reason/location | Waste audits (Felipe) |
| Briefing: stockouts frequency | `stock_threshold_triggered` | Threshold hits by product/location | Adjust min / replenishment |
| Briefing: bypass attempts | `direct_stock_edit_rejected` | Rejects by location | Training/permissions (Jake) |
| Briefing: abnormal price | `ingredient_price_variance_detected` | Variance events by product/supplier | Renegotiate / alternate supplier |
| Tech lead: outbound per day | `outbound_order_created` | Daily counts | Ops staffing / prep planning |
| Tech lead: validation errors by product | `product_validation_failed` | Errors by field/entity/product | UX / rule fixes |
| Tech lead: direct stock edits | `direct_stock_edit_rejected` | Reject volume | Controls reinforcement |
| Tech lead: threshold alerts | `stock_threshold_triggered` | Alert frequency | Threshold tuning |
| Tech lead: failed logins/day | `user_login_failed` | Daily failures | Security controls |
| Tech lead: sections visited most | `page_viewed` | Page hit distribution | IA priorities |
| Tech lead: abandoned flows | `workflow_abandoned` | Abandon rate by workflow/step | Form simplification |
| Assignment: API response times | `api_request_completed` / `api_request_failed` | Latency & error rate | Perf / reliability work |

---

## 11. Shared enums (for implementers)

- `country`: `CO`, `US`
- `currency`: `COP`, `USD` (must match location country: CO→COP, US→USD)
- `product_category`: `protein`, `vegetable`, `sauce`, `beverage`, `packaging`, `cleaning`
- `unit`: `kg`, `unit`, `liter`
- Waste `reason`: `expired`, `kitchen_error`, `theft_suspected`
- Outbound prep `reason`: `prep_consumption`

Country/currency pairing for all six mandatory inventory events is enforced in [`event-schemas.json`](./event-schemas.json) via `definitions.countryCurrencyConsistent` (briefing §6).

Seed-data expectations in briefing §5 apply to later capture/storage milestones; property shapes above are designed so those seeds can emit valid events without re-instrumentation.
