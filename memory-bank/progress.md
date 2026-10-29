# Progress

## Complete on `main` (verified 2026-10-29)

- Root `CONTEXT.md` is the Brasaland company briefing used by apps (kept as-is; not replaced by the old memory-bank branch rewrite).
- `Supplier-Directory-CONTEXT.md` documents the supplier schema.
- Milestone 2 TypeScript utilities under `src/` with root `npm run typecheck` / `npm run demo`.
- `uis/website/` public static site (Tailwind + Brasa Points form).
- `services/api/` FastAPI supplier directory with staff JWT auth (PR #6).
- `uis/backoffice/` supplier desk + staff auth frontend (login, register, profile, session guards) (PR #8).
- Coding-agent memory bank added on branch `feature/agent-memory-bank-only`: `AGENTS.md`, `.agents/`, `memory-bank/` (this change). Backoffice Tailwind restyle from PR #2 was **not** brought forward.

## Intentionally left out of this memory-bank PR

- Any `uis/backoffice` Tailwind/`package.json` restyle from `feature/agent-memory-bank`
- Website visual restyles and submission PNGs from that branch
- Replacement of root `CONTEXT.md`
- Docker / Compose (still unmerged elsewhere)
- Telemetry branches
- Password-reset / second auth stack work
- Talent pipeline tracker

## Integration backlog status

1. Auth frontend / memory bank / talent tracker — landed on `main` (earlier stages).
2. Password-reset port — open as PR #16 (close superseded #7).
3. Error-handling port — open as PR #17 (close superseded #5).
4. **Stage 6a (this change):** port `uis/website` to Next.js React pattern — open as website React PR.
5. **Stage 6b (complete on `feature/backoffice-react-port`):** port `uis/backoffice` to Next.js App Router + TypeScript + Tailwind v4 while preserving supplier, session, profile, and password flows.
6. **Stage 7 (this change):** rewrite Docker Compose from PR #9 into separate API, website, backoffice, and talent services for the final React UI shape.
