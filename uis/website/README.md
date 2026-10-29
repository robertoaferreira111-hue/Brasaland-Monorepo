# Brasaland website

Public Next.js site for Milestone 1, ported to the React conventions established by `uis/talent-pipeline-tracker/`. Facts, field order, and messages come from the root `CONTEXT.md`.

## Setup

```bash
cd uis/website
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

## Scripts

```bash
npm run dev                 # Next.js on port 3000
npm run build               # production build
npm run start               # serve production build on 3000
npm run lint                # ESLint
npx tsc --noEmit            # TypeScript check (scripts/ excluded)
npm run verify:validation   # Brasa Points validation parity checks
```

## Folder structure

```
app/                 # App Router pages (`/`, `/application`)
components/          # SiteHeader, SiteFooter, BrasaPointsForm, …
lib/                 # Pure Brasa Points validation (`brasaPoints.ts`)
public/              # favicon.svg, story.svg
scripts/             # Dev-only verification (not imported by the app)
```

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Landing page (story, locations, menu, Brasa Points CTA, contact) + Restaurant JSON-LD |
| `/application` | Brasa Points registration form |

## Behaviour preserved from the static site

- Landing copy, sections, and JSON-LD
- Brasa Points form validation (full name, email, phone with country-gated country codes, city cascading from country, 18+ DOB, terms)
- Phone format checks wait until a country is selected
- Blocked submit focuses the first invalid field; Clear resets the form
- Success panel after a valid submit

## Styling

Tailwind CSS v4 via `@tailwindcss/postcss` (same stack as the talent pipeline tracker). Fraunces + Source Sans 3 via `next/font`.
