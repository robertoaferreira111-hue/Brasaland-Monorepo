# Talent Tracker API contract

Verified against:

- OpenAPI: `https://playground.4geeks.com/tracker/api/v1/openapi.json` (title **Talent Tracker API**, version **1.0.0**)
- Swagger UI: `https://playground.4geeks.com/tracker/api/v1/docs`
- Live read calls to `https://playground.4geeks.com/tracker/api/v1` (2026-10-05)

Base URL for the app: `NEXT_PUBLIC_API_URL` → `https://playground.4geeks.com/tracker/api/v1` (no trailing slash).

---

## Endpoints used by this milestone

| Method | Path | Purpose | Documented success |
| --- | --- | --- | --- |
| `GET` | `/records` | List / filter / search candidates | `200` |
| `POST` | `/records` | Register candidate | `201` → `RecordOut` |
| `GET` | `/records/{id}` | Candidate detail | `200` |
| `PUT` | `/records/{id}` | Replace candidate fields (`RecordCreate` body) | `200` → `RecordOut` |
| `PATCH` | `/records/{id}` | Update `status` and/or `stage` | `200` → `RecordOut` |
| `GET` | `/records/{id}/notes` | List notes | `200` |
| `POST` | `/records/{id}/notes` | Add note | `201` |
| `DELETE` | `/records/{id}/notes/{note_id}` | Delete note | `204` |

Also present in OpenAPI but **not** required by Milestone 3 UI: `DELETE /records/{id}`.

---

## Query parameters (`GET /records`)

From OpenAPI parameter descriptions (verified live):

| Param | Role | Notes |
| --- | --- | --- |
| `status` | Filter | Allowed values documented: `received`, `in_progress`, `selected`, `discarded` |
| `stage` | Filter | Allowed values documented: `pending`, `review`, `personal_interview`, `technical_interview`, `offer_presented` |
| `search` | Search | OpenAPI: "Search in full_name or email". Live: `search=michael` returned matching names. |
| `page` | Pagination | Default `1`, minimum `1` |
| `limit` | Pagination | Default `20`, minimum `1`, description says "no max limit" |

### List response shape (live)

```json
{
  "total": 100,
  "page": 1,
  "limit": 2,
  "data": [ /* record objects */ ]
}
```

---

## Record shapes

### Create / replace body (`RecordCreate`) — OpenAPI

Required: `full_name`, `email`, `phone`, `position`, `experience_years`  
Optional nullable: `linkedin_url`, `cv_url`

### Patch body (`RecordPatch`) — OpenAPI

Optional nullable: `status`, `stage`

### Record fields

| Field | In OpenAPI `RecordOut` | In live `GET /records` list item | In live `GET /records/{id}` |
| --- | --- | --- | --- |
| `id` | yes | yes | yes |
| `full_name` | yes | yes | yes |
| `email` | yes | yes | yes |
| `phone` | yes | yes | yes |
| `position` | yes | yes | yes |
| `linkedin_url` | yes (string \| null) | yes | yes |
| `cv_url` | yes (string \| null) | yes | yes |
| `status` | yes (string) | yes | yes |
| `stage` | yes (string) | yes | yes |
| `experience_years` | yes (number) | yes | yes |
| `notes_count` | yes (integer) | yes | yes |
| `applied_at` | yes (string) | yes | yes |
| `updated_at` | yes (string) | yes | yes |
| `notes` | **no** | **yes** (array of note objects) | **no** |

**Disagreement:** list responses embed a `notes` array that is absent from the OpenAPI `RecordOut` schema and from live detail (`GET /records/{id}`). Prefer `GET /records/{id}/notes` for the notes UI.

### Note shapes

**Create (`NoteCreate`):** `{ "content": string }` (`minLength: 1`)

**Live note object** (list endpoint and embedded list notes):

```json
{
  "id": "…",
  "record_id": "…",
  "content": "…",
  "created_at": "…"
}
```

**Live notes list response:**

```json
{
  "data": [ /* notes */ ],
  "meta": { "total": 2 }
}
```

---

## Allowed `status` and `stage` values

### As documented (OpenAPI query descriptions + company CONTEXT labels)

| API `status` | UI label (CONTEXT) |
| --- | --- |
| `received` | Received |
| `in_progress` | In progress |
| `selected` | Selected |
| `discarded` | Discarded |

| API `stage` | UI label (CONTEXT) |
| --- | --- |
| `pending` | Pending review |
| `review` | Under review |
| `personal_interview` | Personal interview |
| `technical_interview` | Technical interview |
| `offer_presented` | Offer presented |

OpenAPI schemas type `status` / `stage` as plain `string` (no formal enum). Allowed values above come from query-parameter descriptions and CONTEXT.md.

### Observed in live `GET /records?limit=100` (total 100)

| status | count |
| --- | --- |
| `received` | 66 |
| `in_progress` | 23 |
| `discarded` | 11 |
| `selected` | **0 in this sample** |

| stage | count |
| --- | --- |
| `pending` | 65 |
| `review` | 24 |
| `personal_interview` | 6 |
| `technical_interview` | 5 |
| `offer_presented` | **0 in this sample** |

**Uncertainty:** `selected` and `offer_presented` are documented and required for UI labels, but were not present in the live sample of 100 records. They remain valid API values per OpenAPI/CONTEXT.

---

## Filtering, search, pagination (live checks)

- `status=in_progress&limit=1` → `200`, `total` reduced, sample `status` was `in_progress`.
- `search=michael&limit=2` → `200`, names matched "Michael …".
- Unknown `status=nope` → `200` with `{ "total": 0, "data": [] }` (not a 4xx).

---

## Errors (live + OpenAPI)

| Case | OpenAPI | Live |
| --- | --- | --- |
| Validation | `422` + `HTTPValidationError` (`detail` array of `{ loc, msg, type }`) | Not exhaustively exercised in Phase 0 |
| Missing record `GET /records/{id}` | Documents `200` / `422` only | **`404`** body `{ "error": "Record not found" }` |
| Invalid status filter | — | `200` empty page (see above) |
| Successful note delete | `204` | Not re-verified with a write in Phase 0 (read-only verification preferred for this note) |

**Disagreement:** missing-record behavior is `404` + `{ error }` live, while OpenAPI for `GET /records/{id}` does not document `404`.
