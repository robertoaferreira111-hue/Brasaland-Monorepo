# Brasaland backoffice

Internal procurement directory and staff account app built with Next.js App Router, TypeScript, React 19, and Tailwind CSS v4. Records come from the FastAPI app in `services/api`. Field names, categories, and statuses come from `Supplier-Directory-CONTEXT.md`.

## Run

Start the API from `services/api`:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If the database is empty, load the context suppliers once:

```bash
uv run seed
```

Install and run the backoffice:

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:3001`. Public routes are `/login`, `/register`, `/forgot-password`, and `/reset-password`. The directory and account routes send you to `/login` when no access token is stored. `/account` forwards to `/account/profile`. A protected `401` tries `POST /auth/refresh` once; if refresh fails, the session is cleared and the browser returns to login.

Registration posts optional name, phone, and address with `POST /users`, then signs in with `POST /auth/login`. The profile page reads `GET /auth/me` and saves name, phone, and address with `PUT /profiles/me`.

Demo account after `uv run seed`: `staff@brasaland.com` / `demo-password`.

## API address

The app resolves the supplier API in this order:

1. If the page URL has `?api=...`, that value is used and a trailing slash is removed.
2. On GitHub Codespaces, when the hostname ends with `.app.github.dev`, the port in the hostname is rewritten to `8000` and the page protocol is kept (`https://<name>-8000.app.github.dev`).
3. `NEXT_PUBLIC_API_URL`, when set.
4. Otherwise `http://127.0.0.1:8000`.

Forward API port 8000 in Codespaces. The API allows `https://*.app.github.dev` origins.

## Verify

```bash
npm run build
npx tsc --noEmit
```
