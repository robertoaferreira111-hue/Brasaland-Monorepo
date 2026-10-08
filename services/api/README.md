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

## Install

From `services/api`:

```bash
uv sync
```

## Optional seed

```bash
uv run seed
```

Creates `staff@brasaland.com` / `demo-password` when missing.

## Run API (port 8000)

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Codespaces:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
uv run pytest
```

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
