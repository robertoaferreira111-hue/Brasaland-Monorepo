# Weekly Location Cost & Waste Metrics

Status: business contract and API design only. No reporting table or endpoint is implemented in Part 1.

## Business question

For each Brasaland location in Colombia and Florida, how much did it spend and waste during the most recently completed ISO week, how large was waste relative to purchases, and how often did stockouts or abnormal ingredient-price alerts occur?

The **Weekly Location Cost & Waste Report** is for Mariana Restrepo (CEO) and Felipe Guerrero (Operations Director). It supports weekly comparison, waste-audit prioritization, replenishment review, and supplier-price intervention. It is refreshed every Monday after the preceding UTC ISO week closes.

## Reporting grain and dimensions

- Grain: one row per `location_id` and `week_start`.
- Week: Monday `00:00:00 UTC` through the next Monday, end-exclusive.
- Dimensions: `location_id`, `country`, `week_start`, and `currency`.
- Country/currency pairs: `CO`/`COP` and `US`/`USD`.
- Currency conversion: none. COP and USD rows appear side by side and are never summed into one amount.
- Destination: `reporting.weekly_location_performance`.

The source identity prerequisite is a stable producer `eventId` persisted as `telemetry_events.id` and reused on transmission retries. The current generic capture adapter generates a fresh ID per write, so inventory capture must satisfy this prerequisite before `count(distinct id)` or source deduplication is reliable.

## KPI definitions

### Purchase Cost per Location

- **Business definition:** Cost of ingredients received by one location during one ISO week.
- **Formula:** `sum(quantity * unit_cost)` for valid `inbound_order_created` events.
- **Source:** `telemetry_events.event_type = 'inbound_order_created'`.
- **Fields:** `id`, `timestamp`, `tags.location_id`, `tags.country`, `tags.quantity`, `tags.unit_cost`, `tags.currency`.
- **Dimensions:** location, country, ISO week, currency.
- **Destination field:** `total_purchase_cost`.
- **Unit:** local currency amount (`COP` or `USD`).
- **Frequency:** weekly, published Monday morning.
- **Limitations:** inventory capture is not implemented in the repository; the current approved schema has `unit_cost`, but live availability is not proven. Quantity and unit cost must refer to compatible units.

### Waste Cost per Location

- **Business definition:** Monetary value lost through expired product, kitchen error, or suspected theft at one location during one ISO week.
- **Formula:** `sum(quantity * unit_cost)` for valid `stock_waste_registered` events.
- **Source:** `telemetry_events.event_type = 'stock_waste_registered'`.
- **Fields:** `id`, `timestamp`, `tags.location_id`, `tags.country`, `tags.quantity`, `tags.unit_cost`, `tags.currency`, `tags.reason`.
- **Dimensions:** location, country, ISO week, currency. `reason` is retained for audit drill-down but is not part of the destination grain.
- **Destination field:** `total_waste_cost`.
- **Unit:** local currency amount (`COP` or `USD`).
- **Frequency:** weekly, published Monday morning.
- **Limitations:** `unit_cost` is an additive field in the approved schema contract, but inventory capture is not implemented. The valuation is event-time unit cost, not replacement cost.

### Waste Ratio

- **Business definition:** Share of a location's weekly purchase cost lost as waste.
- **Formula:** `total_waste_cost / total_purchase_cost`; `0` when `total_purchase_cost = 0`.
- **Sources:** derived from the purchase and waste aggregates above.
- **Fields:** `total_purchase_cost`, `total_waste_cost`.
- **Dimensions:** location, country, ISO week, currency.
- **Destination field:** `waste_ratio`.
- **Unit:** decimal ratio (`0.072` means `7.2%`).
- **Frequency:** weekly, published Monday morning.
- **Limitations:** a zero denominator produces `0` per the briefing, but must be interpreted with the purchase total; it does not prove efficient operation. Currency mismatches block calculation for the affected location/week.

### Stockout Frequency

- **Business definition:** Number of times a product at one location crosses below its configured minimum during one ISO week.
- **Formula:** `count(distinct id)` for valid `stock_threshold_triggered` events.
- **Source:** `telemetry_events.event_type = 'stock_threshold_triggered'`.
- **Fields:** `id`, `timestamp`, `tags.location_id`, `tags.country`, `tags.currency`.
- **Dimensions:** location, country, ISO week.
- **Destination field:** `stockout_events_count`.
- **Unit:** event count.
- **Frequency:** weekly, published Monday morning.
- **Limitations:** accuracy depends on capture emitting once per threshold crossing rather than on every below-threshold read. Inventory capture is not implemented in this repository.

### Price Alert Frequency

- **Business definition:** Number of abnormal ingredient-price variance alerts at one location during one ISO week.
- **Formula:** `count(distinct id)` for valid `ingredient_price_variance_detected` events.
- **Source:** `telemetry_events.event_type = 'ingredient_price_variance_detected'`.
- **Fields:** `id`, `timestamp`, `tags.location_id`, `tags.country`, `tags.currency`.
- **Dimensions:** location, country, ISO week.
- **Destination field:** `price_alert_events_count`.
- **Unit:** event count.
- **Frequency:** weekly, published Monday morning.
- **Limitations:** accuracy depends on the upstream historical-price baseline and threshold. The approved event stores those values, but no inventory capture path exists in this repository.

## Source-to-destination mapping

| Destination field | Type | Source/calculation |
| --- | --- | --- |
| `id` | `uuid` | Database-generated row identifier. |
| `location_id` | `text` | Validated `tags.location_id`. |
| `country` | `text` | Validated `tags.country`. |
| `week_start` | `date` | UTC ISO Monday derived from source `timestamp`. |
| `total_purchase_cost` | `numeric` | Sum of inbound `quantity * unit_cost`. |
| `total_waste_cost` | `numeric` | Sum of waste `quantity * unit_cost`. |
| `waste_ratio` | `numeric` | Waste cost divided by purchase cost, or `0` for no purchases. |
| `stockout_events_count` | `integer` | Count of distinct threshold-event source IDs. |
| `price_alert_events_count` | `integer` | Count of distinct price-alert source IDs. |
| `currency` | `text` | `COP` for `CO`; `USD` for `US`. |
| `computed_at` | `timestamptz` | UTC time at which the row was last upserted. |

The destination unique key is `(location_id, week_start)`.

## Missing-data semantics

- A present row with zero counts means the pipeline had a known location and valid source coverage but found no matching events.
- An absent location does **not** mean zero. The repository has no authoritative location registry, so absence may mean no capture, an unknown location, or no activity.
- An invalid KPI-bearing event fails the run before load; no requested week from that run is published with a known understated KPI.
- `data_status: "complete"` means the pipeline successfully processed the available valid source window. It does not claim all 14 locations were observed.
- `coverage: "observed_locations_only"` remains explicit until an authoritative location registry exists.
- Unavailable reporting storage is an HTTP `503`, not a successful payload state.

## Reporting API contracts

These routes are proposed under `services/reporting/`. They remain separate from the unchanged technical `GET /telemetry/report`.

### GET `/reporting/pipeline-runs/latest`

Returns status and metadata for the most recent business-performance run. Proposed service code calls `get_latest_pipeline_run()` from `data/pipelines/business_performance`.

**Success: `200 OK`**

```json
{
  "run_id": "8bb7302d-cbe7-49fc-ae56-3dddb12739a4",
  "pipeline_name": "weekly_location_cost_waste",
  "trigger_type": "schedule",
  "requested_week_start": "2026-07-13",
  "affected_weeks": ["2026-07-06", "2026-07-13"],
  "status": "success",
  "last_completed_stage": "load",
  "started_at": "2026-07-20T06:00:00Z",
  "finished_at": "2026-07-20T06:01:18Z",
  "heartbeat_at": "2026-07-20T06:01:15Z",
  "lease_expires_at": null,
  "watermark_from": "2026-07-06T00:00:00Z",
  "watermark_to": "2026-07-20T00:00:00Z",
  "rows_extracted": 1842,
  "rows_transformed": 28,
  "rows_loaded": 28,
  "rows_rejected": 0,
  "rows_skipped_duplicate": 3,
  "retry_count": 0,
  "error_stage": null,
  "error_summary": null
}
```

**Errors**

- `404 Not Found`: no run has been recorded.
- `503 Service Unavailable`: reporting storage cannot be read.

No stack trace, credential, or raw rejected payload is returned.

### POST `/reporting/pipeline-runs`

Requests a manual run. Proposed service code validates HTTP input and calls `trigger_business_performance_run()` from `data/pipelines/business_performance`; ETL logic stays in `data/pipelines/`.

**Request**

```json
{
  "week_start": "2026-07-13"
}
```

`week_start` is optional. When omitted, it means the most recently completed UTC ISO week. When present, it must be a Monday and cannot identify a future or incomplete week.

**Accepted: `202 Accepted`**

```json
{
  "run_id": "8bb7302d-cbe7-49fc-ae56-3dddb12739a4",
  "pipeline_name": "weekly_location_cost_waste",
  "week_start": "2026-07-13",
  "status": "running",
  "trigger_type": "manual",
  "accepted_at": "2026-07-20T13:15:00Z"
}
```

**Duplicate protection and errors**

- If any `weekly_location_cost_waste` run holds a live lease, return `409 Conflict` with the active `run_id`. Runs are serialized before extraction so overlapping windows cannot overwrite newer results.
- `422 Unprocessable Entity`: invalid JSON, non-Monday date, future week, or incomplete week.
- `503 Service Unavailable`: orchestration or control storage is unavailable.

The destination upsert also makes a repeated completed-week request safe.

### GET `/reporting/weekly-location-performance`

Returns all available location rows for one week. Proposed service code calls `get_weekly_location_performance(week_start)` from `data/pipelines/business_performance`.

**Query**

- `week_start` is optional and must be an ISO date for a Monday.
- If omitted, use the most recent successfully computed week.

**Success: `200 OK`**

```json
{
  "week_start": "2026-07-13",
  "data_status": "complete",
  "coverage": "observed_locations_only",
  "computed_at": "2026-07-20T06:01:17Z",
  "locations": [
    {
      "location_id": "medellin-centro",
      "country": "CO",
      "total_purchase_cost": 8420000,
      "total_waste_cost": 610000,
      "waste_ratio": 0.072,
      "stockout_events_count": 2,
      "price_alert_events_count": 1,
      "currency": "COP"
    }
  ]
}
```

`locations` is sorted by `country`, then `location_id`. Amounts remain in each location's local currency.

**Missing data and errors**

- `200 OK` with `locations: []`, `data_status: "no_rows"`, and `coverage: "observed_locations_only"` when the requested completed week has a successful run but no rows.
- `404 Not Found` when the week has never completed successfully.
- `422 Unprocessable Entity` for an invalid or non-Monday `week_start`.
- `503 Service Unavailable` when reporting storage cannot be read.

Until an authoritative registry exists, the response cannot guarantee that an absent one of the 14 locations had zero activity.
