# Brasaland staff auth API

FastAPI JWT backend for `uis/backoffice`. It implements the endpoints the Next.js client calls today:

- `POST /users` — register `{ email, password }`
- `POST /auth/login` — `{ email, password }` → `{ access_token, refresh_token }`
- `GET /auth/me` — Bearer → profile (`email`, `name`, `phone`, `address`)
- `PUT /profiles/me` — Bearer → update profile fields
- `POST /auth/logout` — Bearer (revokes refresh tokens for that user)
- `POST /auth/refresh` — `{ refresh_token }` → new token pair

Storage is **TinyDB** (`data/auth.json`, gitignored). Passwords use PBKDF2 (stdlib). Tokens use **PyJWT** with `JWT_SECRET` (set in the environment for anything beyond local demo).

CORS allows `http://127.0.0.1:3000`, `http://localhost:3000`, `http://127.0.0.1:3001`, and `http://localhost:3001`, plus Codespaces `https://*.app.github.dev`.
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

## Optional seed
## Seed

```bash
uv run seed
```

Creates `staff@brasaland.com` / `demo-password` when missing.

## Run API (port 8000)

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Codespaces:
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
uv run pytest --cov=app --cov-report=term-missing
```

See [TESTING.md](./TESTING.md) for the AUTH-088 test plan, coverage results, AI-assisted findings, Jest instructions for `uis/backoffice`, and optional extras.

## Quick curl check

```bash
curl -s -X POST http://127.0.0.1:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"email":"curl@brasaland.com","password":"demo-pass"}'

curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"curl@brasaland.com","password":"demo-pass"}'
```

Use the `access_token` from login as `Authorization: Bearer …` on `/auth/me` and `/profiles/me`.
```

## Codespaces

Locally the procurement UI calls `http://127.0.0.1:8000`.

In GitHub Codespaces the UI detects a hostname ending in `.app.github.dev`, rewrites the port in that hostname to `8000`, and keeps the page protocol (`https://<name>-8000.app.github.dev`). The API allows those origins with `allow_origin_regex` for `https://*.app.github.dev`, and still allows `localhost` and `127.0.0.1` on ports 3000 and 3001.

To point the UI at a different API, open it with `?api=...`. A trailing slash on that value is removed.
