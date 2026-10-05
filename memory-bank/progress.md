# Progress

## Complete

- Milestone 1 public site in `uis/website/` (static HTML, Tailwind, `validation.js`). It was already in the repo. This phase did not change it.
- Milestone 2 operations utilities in `src/`, with root scripts `npm run typecheck` and `npm run demo`. Already in the repo. This phase did not change them.
- Root `CONTEXT.md` is the Brasaland company briefing, committed on `feature/agent-memory-bank` as `42b7ecc` ("Use the Brasaland company briefing as the root business source."). That commit contains only `CONTEXT.md`.
- `memory-bank/projectbrief.md`, `memory-bank/techContext.md`, and this file.
- Root `AGENTS.md` with the session read list, the pre-commit workflow, and the paths that need confirmation.
- `.agents/rules/company-facts.md` (always active) and `.agents/rules/uis-apps.md` (file pattern `uis/**`).
- `.agents/skills/add-brasaland-ui-section/SKILL.md`.
- `uis/website/` home copy was aligned to `CONTEXT.md` (static HTML and Tailwind kept). `uis/backoffice` was not part of that change.
- `uis/backoffice/` is an internal desk at `/`: locations by country, department owners and forward work, and the Monday 7am executive report. Its own layout, README, and Tailwind build. It does not import `uis/website`.
- No service under `services/`. The desk does not call an API. The service-layout conflict stays open.

`npm run typecheck` at the repo root exited 0. `npm run build:css` exited 0 in both `uis/website/` and `uis/backoffice/`.

## Not started

- `services/` still has no application, only its template README. The entry views do not need one.

## Planned next

- Open the pull request from `feature/agent-memory-bank` to `main`, with screenshots of both `/` routes and a link to `AGENTS.md`.
- Leave `services/` empty until the service-layout open question is decided.
- Leave product folders `agents/`, `skills/`, `mcps/`, `workflows/`, `data/`, and `infra/` unchanged unless a task names them.
