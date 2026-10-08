# Brasaland supplier directory API

## Folder layout

The sample rubric lists `main.py`, `models.py`, `database.py`, and `seed.py` directly in `services/api/`, and the endpoints in `routes/suppliers.py`. This repo uses an installable package instead:

- `services/api/app/main.py`
- `services/api/app/models.py`
- `services/api/app/database.py`
- `services/api/app/seed.py`
- `services/api/app/routers/suppliers.py` (same HTTP routes; the package is named `routers`, not `routes`)

The behavior matches the rubric. The run command is `uv run uvicorn app.main:app --reload` because the modules live in the `app` package.

## Install

From `services/api`:

```bash
uv sync
```

## Seed

```bash
uv run seed
```

The seed is idempotent. A second run inserts 0.

## Run API

```bash
uv run uvicorn app.main:app --reload
```

On Codespaces, bind every interface so the forwarded port is reachable:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
uv run pytest
```

## Error response contract

Successful responses are unchanged (`SupplierResponse` objects or lists).

Client and server errors use a JSON body with a `detail` field, compatible with the backoffice UI:

| Status | When | `detail` shape |
|--------|------|----------------|
| **422** | Request validation (Pydantic / FastAPI) | Array of validation error objects (unchanged FastAPI shape) |
| **404** | Supplier id not found | String, e.g. `"Supplier not found"` |
| **500** | Storage failure, corrupt stored row on single-resource routes, or unexpected errors | String: `"Storage unavailable"`, `"Stored supplier data is invalid"`, or `"An unexpected error occurred"` |

List endpoints skip corrupt stored rows (logged server-side) and still return **200** with the valid suppliers. Single-resource routes return **500** with a generic message when a stored document cannot be loaded. Tracebacks, filesystem paths, and internal exception types are not included in API responses; they are logged on the server.

The backoffice UI (`uis/backoffice/supplierErrors.mjs`) maps the stable 500/404 detail strings above to longer recovery-oriented copy. If you change those Python constants, update `BACKEND_SAFE_DETAILS` and the contract tests on both sides.

## Codespaces

Locally the procurement UI calls `http://127.0.0.1:8000`.

In GitHub Codespaces the UI detects a hostname ending in `.app.github.dev`, rewrites the port in that hostname to `8000`, and keeps the page protocol (`https://<name>-8000.app.github.dev`). The API allows those origins with `allow_origin_regex` for `https://*.app.github.dev`, and still allows `localhost` and `127.0.0.1` on ports 3000 and 3001.

To point the UI at a different API, open it with `?api=...`. A trailing slash on that value is removed.
