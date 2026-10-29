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

## Planned next (integration backlog — not started here)

1. Close original PR #2 after this PR merges (superseded for the memory-bank portion).
2. Land Milestone 3 talent tracker onto `main`.
3. Port password-reset onto the single auth stack on `main`.
4. Error-handling audit rebase.
5. Later: React ports and Docker rewrite once UIs settle.
