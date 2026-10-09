# Pull request description (copy into GitHub)

**Create PR:** https://github.com/robertoaferreira111-hue/Brasaland-Monorepo/pull/new/feature/password-reset

**Suggested title:** `feat: AUTH-03 password reset and change-password flow`

---

## Summary
- Implements AUTH-03 **The Missing Piece: Password Reset Flow** on the Brasaland FastAPI + TinyDB API and static backoffice UI.
- Adds forgot / reset / authenticated change-password endpoints with bcrypt hashing, hashed single-use reset tokens (15–60 min), anti-enumeration, and Resend email (HTML + text).
- Adds backoffice routes `/login/`, `/forgot-password/`, `/reset-password/`, `/account/change-password/` plus a login **Forgot your password?** link.

## Backend
- `POST /auth/forgot-password`, `POST /auth/reset-password`, `POST /auth/change-password`
- Supporting `POST /auth/login` (Bearer JWT)
- TinyDB tables `users` and `password_reset_tokens` (SHA-256 of raw token only)
- In-process rate limit on forgot-password (5 / email / 15 min)
- Env-driven config via `.env.example` / `.env/local` (never committed)

## Frontend
- Static pages under `uis/backoffice/` matching assignment routes
- Shared client helpers in `js/auth-api.js` (payloads, validation, duplicate-submit guard)

## Email provider & env vars
- **Provider:** Resend
- **API key variable:** `RESEND_API_KEY`
- Also required: `EMAIL_FROM`, `FRONTEND_URL`, `JWT_SECRET`, `RESET_TOKEN_EXPIRE_MINUTES`

## Database / migrations
- No SQL migrations (TinyDB document tables created on use)

## Tests (actual)
```bash
cd services/api && uv run pytest -q
# 37 passed

cd uis/backoffice && npm test
# 15 passed
```

## Security
- Anti-enumeration identical 200 confirmation copy (rubric wording)
- Single-use consume + concurrent protection; bcrypt passwords; secrets gitignored
- Provider failures return 503 without claiming success
- End-to-end email delivery verified with Resend before submission

## Manual verification
- [x] Automated backend + frontend suites
- [x] Live Resend reset email sent successfully
- [x] Acceptance notes in `docs/submission/password-reset-acceptance.md`

## Test plan
- [ ] `uv run pytest` in `services/api`
- [ ] `npm test` in `uis/backoffice`
- [ ] Seed + run API/UI; exercise forgot → email link → reset → login
- [ ] Confirm change-password rejects wrong current password
- [ ] Confirm unknown email shows the same confirmation message
- [ ] Confirm `.env/local` is not in the PR diff
