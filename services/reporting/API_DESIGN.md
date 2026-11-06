# Reporting API Integration Design

Status: Phase 5 design only. This document proposes three business reporting API contracts under `services/reporting/`. No route, router, model, migration, or dependency is implemented in Part 1. KPI definitions and destination fields remain those established in Phase 2 (`docs/telemetry/business_metrics.md`, `reporting.weekly_location_performance`).

## 1. Service boundary

| Concern | Boundary |
| --- | --- |
| Proposed module | `services/reporting/` |
| Host application | Existing `services/api` FastAPI app |
| Auth | Reuse current staff JWT/session dependencies; not a second auth stack |
| Pipeline functions | Proposed imports from `data/pipelines/business_performance` |
| Destination reads/writes | `reporting.weekly_location_performance`, `reporting.pipeline_runs` |
| Technical reporting | Existing `GET /telemetry/report` in `services/telemetry/`; unchanged and not imported |

Proposed module layout (names only; not created in Part 1):

- `services/reporting/router.py` — HTTP routes
- `services/reporting/schemas.py` — request/response models
- `services/reporting/deps.py` — staff auth dependency reuse

## 2. Coexistence with technical reporting

| Capability | Route | Module | Purpose |
| --- | --- | --- | --- |
| Technical telemetry report | `GET /telemetry/report` | `services/telemetry/` | Engineering metrics over raw `telemetry_events` (events/day, error rates, dimensions, auth failures). Unauthenticated today. Cached 60s. |
| Business pipeline status | `GET /reporting/pipeline-runs/latest` | `services/reporting/` | Operational status of the Weekly Location Cost & Waste pipeline. |
| Business pipeline trigger | `POST /reporting/pipeline-runs` | `services/reporting/` | Manual/backfill trigger into Prefect orchestration. |
| Business KPI query | `GET /reporting/weekly-location-performance` | `services/reporting/` | Location/week Purchase Cost, Waste Cost, Waste Ratio, Stockout Frequency, and Price Alert Frequency. |

Rules:

1. `GET /telemetry/report` keeps its current method, path, query parameters, response shape, cache behavior, and error mapping (`422` / `503` / `500`). Part 1 does not modify `services/telemetry/analysis.py`, `services/telemetry/router.py`, or related tests.
2. Business routes never call technical analysis helpers and never write to `telemetry_events`.
3. Both surfaces may later share the same FastAPI process and Supabase credentials, but they remain separate contracts, destinations, and consumers (engineering vs Mariana/Felipe weekly operations).
4. Mounting `services/reporting/` into `services/api` is a future packaging step; it does not replace or wrap the telemetry router.

## 3. Endpoint 1 — Pipeline status

### Contract

| Item | Value |
| --- | --- |
| HTTP method | `GET` |
| Route | `/reporting/pipeline-runs/latest` |
| Auth | Staff Bearer access token (proposed) |
| Pipeline function | `get_latest_pipeline_run()` |
| Success status | `200 OK` |
| Empty status | `404 Not Found` when no run exists |
| Storage failure | `503 Service Unavailable` |

### Response fields

| Field | Meaning |
| --- | --- |
| `run_id` | Run identifier correlating API, Prefect, and destination audit. |
| `status` | Current or most recent execution status: `running`, `success`, or `failed`. |
| `started_at` | Execution start timestamp (UTC). |
| `finished_at` | Execution end timestamp (UTC), or `null` while running. |
| `error_stage` | Stage that failed, or `null`. |
| `error_summary` | Sanitized error information, or `null`. No credentials or raw payloads. |

Also returned for operators: `pipeline_name`, `trigger_type`, `requested_week_start`, `affected_weeks`, `last_completed_stage`, heartbeat/lease fields, watermarks, and row counters from Phase 3 observability.

### Representative success response

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
  "duration_ms": 78000,
  "error_stage": null,
  "error_summary": null
}
```

### Representative failed-run response

```json
{
  "run_id": "c1f0a9e2-4d55-4b1a-9f0e-2a6c8d1e7b90",
  "pipeline_name": "weekly_location_cost_waste",
  "trigger_type": "manual",
  "requested_week_start": "2026-07-13",
  "affected_weeks": ["2026-07-13"],
  "status": "failed",
  "last_completed_stage": "extract",
  "started_at": "2026-07-20T13:15:00Z",
  "finished_at": "2026-07-20T13:15:42Z",
  "heartbeat_at": "2026-07-20T13:15:40Z",
  "lease_expires_at": null,
  "watermark_from": "2026-07-13T00:00:00Z",
  "watermark_to": "2026-07-20T00:00:00Z",
  "rows_extracted": 0,
  "rows_transformed": 0,
  "rows_loaded": 0,
  "rows_rejected": 0,
  "rows_skipped_duplicate": 0,
  "retry_count": 3,
  "duration_ms": 42000,
  "error_stage": "extract",
  "error_summary": "Source connection exhausted after 3 attempts"
}
```

### Errors

| Status | Condition |
| --- | --- |
| `401 Unauthorized` | Missing or invalid staff token. |
| `404 Not Found` | No pipeline run has been recorded. |
| `503 Service Unavailable` | Reporting control storage cannot be read. |

## 4. Endpoint 2 — Manual pipeline trigger

### Contract

| Item | Value |
| --- | --- |
| HTTP method | `POST` |
| Route | `/reporting/pipeline-runs` |
| Auth | Staff Bearer access token (proposed) |
| Pipeline function | `start_pipeline_run()` |
| Success status | `202 Accepted` |
| Body content type | `application/json` |

FastAPI validates the payload and requests the Prefect deployment/adapter. It does not execute extract/transform/load inline.

### Request payload

```json
{
  "week_start": "2026-07-13",
  "trigger_type": "backfill"
}
```

| Field | Required | Validation |
| --- | --- | --- |
| `week_start` | No | ISO date for a Monday. When omitted, the run is `manual` and uses the schedule window (the last two completed UTC weeks). Must not identify a future or incomplete week. |
| `trigger_type` | No | Omitted week: `manual`. Explicit week: `backfill`. `schedule` is the no-argument command and is rejected on this route. A mismatched pair is `422`. |

### Trigger response

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

Clients use the returned `run_id` for correlation. Part 1 documents `GET /reporting/pipeline-runs/latest` as the status contract. A later `GET /reporting/pipeline-runs/{run_id}` is recommended for Part 2 so a client can observe a specific accepted run without racing a newer schedule or manual trigger. Until that route exists, `/latest` is authoritative only while it still reports the same `run_id`.

### Duplicate-trigger protection

If any `weekly_location_cost_waste` run holds a live renewable lease, the endpoint returns `409 Conflict` with the active run identifier and does not start a second extract. Serialization begins before extraction, matching Phase 3/4 lease behavior.

```json
{
  "detail": {
    "code": "pipeline_run_in_progress",
    "message": "A weekly_location_cost_waste run already holds a live lease",
    "active_run_id": "8bb7302d-cbe7-49fc-ae56-3dddb12739a4"
  }
}
```

After a successful completed week, a later manual request for the same `week_start` is allowed once the lease is free; destination upsert and reconcile deletes keep the recomputation safe.

### Error responses

| Status | Condition |
| --- | --- |
| `401 Unauthorized` | Missing or invalid staff token. |
| `409 Conflict` | Live lease held by another run; body includes `active_run_id`. |
| `422 Unprocessable Entity` | Invalid JSON, non-Monday `week_start`, future week, incomplete week, or disallowed `trigger_type`. |
| `503 Service Unavailable` | Orchestration adapter or control storage unavailable. |

## 5. Endpoint 3 — Business KPI query

### Contract

| Item | Value |
| --- | --- |
| HTTP method | `GET` |
| Route | `/reporting/weekly-location-performance` |
| Auth | Staff Bearer access token (proposed) |
| Pipeline function | `get_weekly_location_performance(...)` |
| Success status | `200 OK` |
| Source table | `reporting.weekly_location_performance` |

### Query parameters

| Parameter | Required | Role |
| --- | --- | --- |
| `week_start` | No | ISO Monday of the requested week. Defaults to the most recent successfully computed week when omitted. Must be a Monday and a completed week. |
| `location_id` | No | Requested location dimension filter. Exact match. |
| `country` | No | Requested country dimension filter. Allowed values: `CO`, `US`. |

The route accepts one week. `week_start` selects that Monday. When it is omitted, the route returns the latest published week.

### Requested dimensions and KPI values

Each location returns the eight briefing fields. `week_start` is the top-level week, not a field on each location. There is no `computed_at` in the JSON.

- `location_id`, `country`, `total_purchase_cost`, `total_waste_cost`, `waste_ratio`, `stockout_events_count`, `price_alert_events_count`, `currency`

Amounts remain in local currency. COP and USD are never summed. The list is locations observed in telemetry for that week. A location with no events is absent, and that absence is not a zero.

### Representative request

```http
GET /reporting/weekly-location-performance?week_start=2026-07-13
Authorization: Bearer <staff_access_token>
```

### Representative success response

```json
{
  "week_start": "2026-07-13",
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

`locations` is sorted by `country`, then `location_id`, within the requested week.

### Missing-data behavior

| Situation | Behavior |
| --- | --- |
| No published rows for the requested week, including an empty table | `404 Not Found`, detail `No published week in the requested range`. |
| Present row with zero KPI counts | Meaningful zero for an observed location/week, not absence. |
| Absent location among the 14 | Not interpreted as zero. There is no location registry; the response lists observed locations only. |
| `week_start` is not a Monday, is not a date, or is not a completed week | `422 Unprocessable Entity`. A non-Monday uses detail `{name} must be a Monday`. |
| Reporting storage unavailable | `503 Service Unavailable`, not an empty success payload. |

### Validation and error responses

| Status | Condition |
| --- | --- |
| `401 Unauthorized` | Missing or invalid staff token. |
| `404 Not Found` | No successfully published data for the requested week range. |
| `422 Unprocessable Entity` | Non-Monday `week_start`, incomplete/future week, or invalid `country`. |
| `503 Service Unavailable` | Destination storage cannot be read. |

## 6. Proposed function mapping

| Endpoint | Proposed pipeline function |
| --- | --- |
| `GET /reporting/pipeline-runs/latest` | `get_latest_pipeline_run()` |
| `POST /reporting/pipeline-runs` | `start_pipeline_run(week_start, trigger_type)` |
| `GET /reporting/weekly-location-performance` | `get_weekly_location_performance(week_start, week_start, location_id, country)` |

ETL logic stays in `data/pipelines/` and `data/process/`. `services/reporting/` performs HTTP validation and serialization only.

## 7. Phase 5 acceptance summary

- Three endpoint contracts are documented under `services/reporting/`.
- Methods, routes, payloads, responses, duplicate protection, missing-data rules, and errors are defined.
- Examples use Phase 2 metrics and `reporting.weekly_location_performance` fields.
- `GET /telemetry/report` remains a separate, unchanged technical capability.
- No new API endpoint is implemented in this phase.
