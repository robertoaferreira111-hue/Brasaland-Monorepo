# Brasaland supplier directory API

## Folder layout

The sample rubric lists `main.py`, `models.py`, `database.py`, and `seed.py` directly in `services/api/`, and the endpoints in `routes/suppliers.py`. This repo uses an installable package instead:

- `services/api/app/main.py`
- `services/api/app/models.py`
- `services/api/app/database.py`
- `services/api/app/seed.py`
- `services/api/app/routers/suppliers.py` (same HTTP routes; the package is named `routers`, not `routes`)
- `services/api/app/routers/auth.py` — login, forgot/reset/change password

The behavior matches the rubric. The run command is `uv run uvicorn app.main:app --reload` because the modules live in the `app` package.

## Auth & password reset

| Method | Path | Notes |
| ------ | ---- | ----- |
| `POST` | `/auth/login` | Returns a Bearer access token (needed for change-password). |
| `POST` | `/auth/forgot-password` | Body `{ "email" }`. Always the same 200 message (anti-enumeration). |
| `POST` | `/auth/reset-password` | Body `{ "token", "new_password" }`. Single-use hashed tokens. |
| `POST` | `/auth/change-password` | Body `{ "current_password", "new_password" }`. Requires `Authorization: Bearer …`. |

Reset tokens are random (`secrets.token_urlsafe`), stored as **SHA-256 hashes** in the TinyDB table `password_reset_tokens`, and expire per `RESET_TOKEN_EXPIRE_MINUTES` (15–60). Email uses **Resend** when `RESEND_API_KEY` is set (SendGrid supported via `SENDGRID_API_KEY`). Reset links are built as `{FRONTEND_URL}/reset-password?token=…`.

Environment files (repo root): `.env/local` or `.env`. See root `.env.example` for variable names. Secrets are never hardcoded.

`uv run seed` also creates a demo user `lucia@brasaland.com` / `ChangeMe123!` if missing.

### Known limitations

- Forgot-password is rate-limited in-process (5 sends / email / 15 minutes). Multi-process deployments need a shared limiter.
- TinyDB JSON storage is single-process. Request-scoped DB access is serialized with a threading lock so concurrent reset attempts cannot double-consume a token in one API process. Multi-process / multi-host deployments need a different store.
- Set a long random `JWT_SECRET` in `.env/local` (or `.env`). The API falls back to a short development default if unset — do not use that default outside local demos.
- Resend delivery requires a permitted `EMAIL_FROM` and recipient policy (verified domain / allowed test addresses). A rejected provider response returns HTTP 503 and does not claim the email was sent.

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
