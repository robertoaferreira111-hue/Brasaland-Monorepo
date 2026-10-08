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

## Codespaces

Locally the procurement UI calls `http://127.0.0.1:8000`.

In GitHub Codespaces the UI detects a hostname ending in `.app.github.dev`, rewrites the port in that hostname to `8000`, and keeps the page protocol (`https://<name>-8000.app.github.dev`). The API allows those origins with `allow_origin_regex` for `https://*.app.github.dev`, and still allows `localhost` and `127.0.0.1` on ports 3000 and 3001.

To point the UI at a different API, open it with `?api=...`. A trailing slash on that value is removed.
