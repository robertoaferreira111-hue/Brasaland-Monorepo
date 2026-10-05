# Company context for the UI

Source: Brasaland Milestone 3 CONTEXT (`.project_instructions/Milestone 3_Talent Pipeline Tracker/context/CONTEXT.md` and `uis/talent-pipeline-tracker/CONTEXT.md`).

## Company and product framing

| Item | Value |
| --- | --- |
| Company | **Brasaland** — grilled food restaurant chain (Colombia + Florida) |
| Internal tech unit | **Brasaland Digital** |
| Stakeholder | Ashley Turner, **People Manager** (CTO Nicolás Park on copy) |
| Product framing | Internal **Brasaland People & Talent** tool (not a generic tracker) |
| Active search | **Executive Assistant**, corporate headquarters, **Medellín** |
| Profile focus | Executive support, calendar/travel management, professional English |

UI chrome, page titles, and copy should read as an internal People & Talent tool for Brasaland Digital — for example “Brasaland People & Talent”, “Executive Assistant pipeline · Medellín HQ”.

## Glossary: API terms → company UI language

| API / technical term | Use in the UI |
| --- | --- |
| Record / `records` | **Candidate** (People & Talent pipeline language). Keep API paths as `/records`; do not rename backend resources. |
| `full_name` | Candidate **name** / full name |
| `email`, `phone`, `position` | Email, phone, position (applied-for role; active campaign is Executive Assistant) |
| `linkedin_url`, `cv_url` | LinkedIn profile, CV |
| `experience_years` | Years of experience |
| `status` | Pipeline **status** — show CONTEXT labels only, never raw API values |
| `stage` | Pipeline **stage** — show CONTEXT labels only, never raw API values |
| `applied_at` | Application date |
| `notes` / notes endpoints | **Internal notes** (after calls or interviews). Notes belong on the candidate detail view only. |
| Filter / search | Filter by status and stage; search by name or email — without full page reloads |

## Status and stage labels (must appear in the UI)

| API `status` | UI label |
| --- | --- |
| `received` | Received |
| `in_progress` | In progress |
| `selected` | Selected |
| `discarded` | Discarded |

| API `stage` | UI label |
| --- | --- |
| `pending` | Pending review |
| `review` | Under review |
| `personal_interview` | Personal interview |
| `technical_interview` | Technical interview |
| `offer_presented` | Offer presented |

## Acceptance notes from CONTEXT

- Raw API values such as `in_progress` or `personal_interview` must never be visible in the interface.
- Registration form must include all fields required by the API (`full_name`, `email`, `phone`, `position`, `experience_years`; optional `linkedin_url`, `cv_url`).
- The mock API is shared across course company contexts; field names and values follow the backend contract (see `docs/API-CONTRACT.md`). No field renaming on the wire.
