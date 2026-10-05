# Brasaland People & Talent — Talent Pipeline Tracker

Internal Next.js app for **Brasaland Digital** / **People & Talent** (Ashley Turner’s Executive Assistant search, Medellín HQ). It consumes the shared Talent Tracker API so the team can list, filter, review, note, register, and edit applicants without spreadsheets.

## Setup

```bash
cd uis/talent-pipeline-tracker
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | API base URL, no trailing slash. Default: `https://playground.4geeks.com/tracker/api/v1` |

`.env.local` is gitignored. Do not commit it.

## Scripts

```bash
npm run dev      # local development
npm run build    # production build
npm run start    # serve production build
npm run lint     # ESLint (app only; scripts/ ignored)
npx tsc --noEmit # TypeScript check (scripts/ excluded)
```

## Folder structure

```
app/                 # App Router pages
components/          # UI
hooks/               # useAsync
lib/                 # httpClient, labels, validation, listNavigation
services/            # typed API functions (records, notes)
types/               # API TypeScript types
docs/                # API-CONTRACT.md, COMPANY-CONTEXT.md
scripts/             # Dev-only live-API verification (not imported by the app)
```

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Applicant list (filters, search, pagination) |
| `/candidates/[id]` | Detail, status/stage PATCH, internal notes |
| `/candidates/[id]/edit` | Edit form (`PUT`) |
| `/candidates/new` | Register form (`POST`) |

## URL state (list)

Query params on `/`:

- `status` — API status value
- `stage` — API stage value
- `search` — name or email (debounced before writing to the URL)
- `page` — 1-based page (`limit` is fixed at 20 in the UI)

Detail links carry `?return=<encoded list query>` so “Candidates” restores the previous list view.

## Data access

Components and feature UI call **`/services`** only. HTTP lives in **`lib/httpClient.ts`** (`fetch` is not used elsewhere). Async UI state uses **`hooks/useAsync.ts`**.

## Dev-only verification scripts

Files under `scripts/` (`verify-phase1.ts`, `verify-phase3.ts`, `verify-phase4.ts`) call the **live** Talent Tracker API. They create clearly marked test records, assert behavior, and delete those records.

- **Not imported** by the Next.js app
- **Excluded** from ESLint (`eslint.config.mjs`) and from `tsc` (`tsconfig.json` `exclude`)
- Run manually, for example: `npx tsx scripts/verify-phase4.ts`

Do not run them against production data you care about; they write to the shared playground API.

## Known API quirks

Documented in `docs/API-CONTRACT.md`:

- OpenAPI `RecordOut` omits `notes[]`, but **list** responses may embed `notes[]`. The app uses `/records/:id/notes` instead.
- Missing record → live `404` `{ "error": "Record not found" }` (not fully documented in OpenAPI).
- `limit` has no practical maximum in live probes; the UI paginates with `limit=20`.
- Sample datasets may lack `selected` / `offer_presented` rows; those values remain valid per OpenAPI/CONTEXT.
- The API can accept an empty-string `full_name` when the key is present; the UI still requires a non-empty name.

## Context

See `CONTEXT.md` and `docs/COMPANY-CONTEXT.md` for Brasaland People & Talent framing and status/stage UI labels (never show raw API enums in the interface).
