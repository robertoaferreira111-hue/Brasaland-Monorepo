# Brasaland supplier directory API

Staff JWT auth and the supplier directory share this FastAPI app. Supplier routes require a bearer access token. Register, login, refresh, and `/health` stay public.

## Folder layout

- `services/api/app/main.py`
- `services/api/app/models.py` — supplier schema and staff auth models
- `services/api/app/database.py` — TinyDB tables `suppliers`, `users`, `refresh_tokens`, and `password_reset_tokens`
- `services/api/app/seed.py`
- `services/api/app/security.py` — PBKDF2 passwords, reset-token hashing, and PyJWT
- `services/api/app/config.py` / `email.py` / `rate_limit.py` / `reset_tokens.py` — password recovery
- `services/api/app/deps.py` — `current_user_email`
- `services/api/app/routers/suppliers.py` — protected supplier routes
- `services/api/app/routers/users.py` — `POST /users`
- `services/api/app/routers/auth.py` — login, logout, refresh, `/auth/me`, forgot/reset/change password
- `services/api/app/routers/profiles.py` — `PUT /profiles/me`

## Install

From `services/api`:

```bash
uv sync
```

## Seed

```bash
uv run seed
```

The supplier seed is idempotent. A second run inserts 0 suppliers. The same command creates `staff@brasaland.com` / `demo-password` when that account is missing.

## Run API

```bash
uv run uvicorn app.main:app --reload
```

On Codespaces, bind every interface so the forwarded port is reachable:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Auth

- `POST /users` — register `{ email, password, name?, phone?, address? }`
- `POST /auth/login` — `{ email, password }` → `{ access_token, refresh_token }`
- `GET /auth/me` — Bearer profile
- `PUT /profiles/me` — Bearer profile update
- `POST /auth/logout` — Bearer, revokes refresh tokens
- `POST /auth/refresh` — `{ refresh_token }` → new token pair
- `POST /auth/forgot-password` — `{ email }` (same message whether or not the account exists)
- `POST /auth/reset-password` — `{ token, new_password }`
- `POST /auth/change-password` — Bearer `{ current_password, new_password }`
- `/suppliers` — every method requires `Authorization: Bearer <access_token>`

Set `JWT_SECRET` outside local demo use. For recovery email delivery, set `RESEND_API_KEY` (or `SENDGRID_API_KEY`), `EMAIL_FROM`, and `FRONTEND_URL` (see repo `.env.example`).

## Tests

```bash
uv run pytest
```

See [TESTING.md](./TESTING.md) for the AUTH-088 cases.

## Codespaces

Locally the procurement UI calls `http://127.0.0.1:8000`.

In GitHub Codespaces the UI detects a hostname ending in `.app.github.dev`, rewrites the port in that hostname to `8000`, and keeps the page protocol (`https://<name>-8000.app.github.dev`). The API allows those origins with `allow_origin_regex` for `https://*.app.github.dev`, and still allows `localhost` and `127.0.0.1` on ports 3000 and 3001.

To point the UI at a different API, open it with `?api=...`. A trailing slash on that value is removed.
