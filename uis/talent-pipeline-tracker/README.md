# Brasaland People & Talent — Talent Pipeline Tracker

Internal frontend for Ashley Turner (People Manager) to manage the Executive Assistant selection process at Brasaland corporate headquarters in Medellín.

## Stack

- Next.js (App Router)
- React
- TypeScript
- Tailwind CSS

## Setup

```bash
cd uis/talent-pipeline-tracker
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment

| Variable | Description |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Talent Tracker API base URL (no trailing slash) |

Default API: `https://playground.4geeks.com/tracker/api/v1`

Do not commit `.env.local`.

## Features

- Candidate list with status/stage filters and name/email search (URL query params, no full reload)
- Candidate detail with PATCH status/stage controls
- Internal notes (list, add, delete)
- Register and edit candidates (POST / PUT) with validation and feedback

## Context

See [CONTEXT.md](./CONTEXT.md) for company framing, label mapping, and acceptance criteria.
