# Progress

## Complete on `main` (verified 2026-11-03)

- Root `CONTEXT.md` is the Brasaland company briefing used by apps (kept as-is; not replaced by the old memory-bank branch rewrite).
- `Supplier-Directory-CONTEXT.md` documents the supplier schema.
- Milestone 2 TypeScript utilities under `src/` with root `npm run typecheck` / `npm run demo`.
- Milestone 3 talent pipeline tracker under `src/` (PR #15).
- Coding-agent memory bank: `AGENTS.md`, `.agents/`, `memory-bank/` (PR #14).
- `services/api/` FastAPI supplier directory with staff JWT auth, password reset, and hardened error contract (PRs #6, #16, #17).
- `pytest-cov` available via API dev deps; coverage: `uv run pytest --cov=app --cov-report=term-missing` (PR #19).
- `uis/website/` public Next.js App Router site + Brasa Points (PR #18).
- `uis/backoffice/` Next.js App Router staff desk (supplier directory, session, profile, password flows) (PR #21).
- Docker Compose rewrite for API + website + backoffice + talent services (PR #20). Superseded static Compose PR #9 closed without merge.
- Telemetry capture, Pandas technical analysis, `GET /telemetry/report`, and backoffice telemetry dashboard (PR #25).
- Business performance pipeline design for the Weekly Location Cost & Waste Report under `data/pipelines/` and `docs/telemetry/`.

## Intentionally left out / deferred

- Telemetry PRs #10–#13 were **closed without merge** so telemetry can be redone from scratch on the current stack (superseded by the Phase 0.5–3 redo on `feature/telemetry-report`).
- Any `uis/backoffice` Tailwind/`package.json` restyle from the old `feature/agent-memory-bank` branch (superseded by the Next.js port).
- Website visual restyles and submission PNGs from that branch.
- Replacement of root `CONTEXT.md`.
- Catalogue still has no `staff_login_succeeded`; auth failure rate uses recorded failure attempts only.

## Integration backlog status

1. Auth frontend / memory bank / talent tracker — **done** on `main`.
2. Password-reset port — **merged** as PR #16 (superseded #7 closed).
3. Error-handling port — **merged** as PR #17 (superseded #5 closed).
4. Stage 6a website React — **merged** as PR #18.
5. Stage 6b backoffice React — **merged** as PR #21.
6. Stage 7 Docker Compose rewrite — **merged** as PR #20 (superseded #9 closed).
7. Stage 5 gap (pytest-cov) — **merged** as PR #19.
8. Telemetry technical report — **merged** as PR #25 (capture, Pandas analysis, `GET /telemetry/report` + 60s cache, auth failure metric, backoffice `/telemetry` dashboard).
9. Business performance pipeline Part 1 design — **complete** (`data/pipelines/PIPELINE_DESIGN.md`, `docs/telemetry/business_metrics.md`, and `docs/telemetry/PREFECT_DESIGN.md`).
