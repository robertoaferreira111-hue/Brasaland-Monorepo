# Brasaland supplier directory

Internal procurement directory for Lucía Fernández. Static HTML, CSS, and JavaScript. Records come from the FastAPI app in `services/api`. Field names, categories, and statuses come from `Supplier-Directory-CONTEXT.md`.

## Run

Start the API from `services/api`:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If the database is empty, load the context suppliers once:

```bash
uv run seed
```

Serve this folder:

```bash
npx http-server . -p 3001 -a 0.0.0.0
```

Open `http://127.0.0.1:3001`.

## Auth & password recovery pages

Folder routes (served by `http-server` as clean paths):

| Path | Page |
| ---- | ---- |
| `/login/` | Sign in (`POST /auth/login`) + “Forgot your password?” link |
| `/forgot-password/` | Request reset email (`POST /auth/forgot-password`) |
| `/reset-password/?token=…` | Set new password (`POST /auth/reset-password`) |
| `/account/change-password/` | Authenticated change (`POST /auth/change-password`) |

Shared client helpers live in `js/auth-api.js` (payloads, validation, Bearer token). Access tokens are stored in `localStorage` under `brasaland_access_token`. Reset tokens are read from the query string and are never logged.

Demo user from API seed: `lucia@brasaland.com` / `ChangeMe123!`.

### Frontend tests

**Vitest** is a devDependency so pure helpers and API payload contracts can be tested without a browser automation stack.

```bash
npm install
npm test
```

## API address

The page resolves the supplier API in this order:

1. If the page URL has `?api=...`, that value is used and a trailing slash is removed.
2. On GitHub Codespaces, when the hostname ends with `.app.github.dev`, the port in the hostname is rewritten to `8000` and the page protocol is kept (`https://<name>-8000.app.github.dev`).
3. Otherwise the API base is `http://127.0.0.1:8000`.

Forward API port 8000 in Codespaces. The API allows `https://*.app.github.dev` origins.

To point the UI at a different API, open it with `?api=...`. A trailing slash on that value is removed.
