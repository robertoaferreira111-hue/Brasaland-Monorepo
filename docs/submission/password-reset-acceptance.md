# AUTH-03 — Password Reset Flow — Submission acceptance

## Status

**READY** — Rubric requirements implemented, automated tests green, and live Resend email delivery confirmed by the submitter.

## Rubric checklist

| Rubric item | Evidence | Result |
| --- | --- | --- |
| Forgot-password sends a real email | Resend integration (`RESEND_API_KEY`); live send confirmed | PASS |
| Hides whether the email exists | Same `200` body for known/unknown | PASS |
| Reset handles expiry | Tokens expire in 15–60 min (`RESET_TOKEN_EXPIRE_MINUTES`) | PASS |
| Reset single-use | `consume_valid_token` + concurrent test | PASS |
| Change-password verifies current password | `POST /auth/change-password` | PASS |
| Frontend forms + success/failure states | Backoffice routes under `uis/backoffice/` | PASS |
| Login “Forgot your password?” link | `uis/backoffice/login/index.html` | PASS |
| API keys via environment variables | `.env.example` + ignored `.env/local` | PASS |

## Endpoints

- `POST /auth/forgot-password` `{ "email" }`
- `POST /auth/reset-password` `{ "token", "new_password" }`
- `POST /auth/change-password` `{ "current_password", "new_password" }` (Bearer)
- Supporting: `POST /auth/login`

## Frontend routes

- `/login/`
- `/forgot-password/`
- `/reset-password/?token=…`
- `/account/change-password/`

## Email provider

- **Service:** Resend
- **Env var:** `RESEND_API_KEY`
- Also used: `EMAIL_FROM`, `FRONTEND_URL`, `JWT_SECRET`, `RESET_TOKEN_EXPIRE_MINUTES`

## Test commands (recorded)

```bash
cd services/api && uv run pytest -q
# 36+ passed

cd uis/backoffice && npm test
# 15 passed
```

## How to demo locally

```bash
# API
cd services/api
uv sync
uv run seed
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# UI
cd uis/backoffice
npx http-server . -p 3001 -a 0.0.0.0
```

Open `http://127.0.0.1:3001/login/`. Demo seed user: `lucia@brasaland.com` / `ChangeMe123!` (or your Resend-allowed account email if updated in seed).
