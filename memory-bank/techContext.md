# Technical context

Facts in this file were checked against the repository on `main` after PR #6 and PR #8. Company facts belong in `CONTEXT.md`, `Supplier-Directory-CONTEXT.md`, and `memory-bank/projectbrief.md`. If a command or path is not listed here, do not invent it.

## Stack that is declared

There is no root workspace file and no `workspaces` field in the root `package.json`. Each manifest stands alone.

| Location | Declared stack |
| --- | --- |
| Repo root, package name `brasaland-operations` | TypeScript `^5.8.2` and `tsx` `^4.19.3` (devDependencies). Milestone 2 utilities under `src/`. |
| `tsconfig.json` | Target `ES2022`, `module` `ESNext`, `strict` true, `noEmit` true, `rootDir` `src`, `include` `src/**/*.ts`. Excludes `uis`, `packages`, `agents`, `skills`. |
| `uis/website`, package name `brasaland-website` | Static HTML + Tailwind `3.4.17` compiled to `styles.css`. See `uis/website/README.md`. |
| `uis/backoffice` | Static HTML/CSS/JS staff desk (supplier directory + auth UI). Has `README.md`, `styles.css`, `js/session.js`, login/register/account/profile pages. **No** `package.json` on current `main` (Tailwind CLI restyle from the old memory-bank branch was not merged). |
| `services/api`, package name `brasaland-supplier-api` | FastAPI + Pydantic + PyJWT + TinyDB + Uvicorn. Python `>=3.12`. Managed with **uv** (`pyproject.toml` + `uv.lock`). |
| `packages/shared/package.json` | `@repo/shared-types`. Empty scripts. |
| `.devcontainer/devcontainer.json` | Ubuntu 24.04, Python 3.12, Node 22. Forwarded ports 3000, 8000, 5678. |

## Commands that exist

| Command | Where | Source |
| --- | --- | --- |
| `npm run typecheck` | Repo root | `tsc --noEmit` on `src/` only |
| `npm run demo` | Repo root | `node --import tsx src/demo.ts` |
| `npm run build:css` | `uis/website/` | Tailwind build for the public site |
| `npx http-server . -p 3000 -a 0.0.0.0` | `uis/website/` | Documented in `uis/website/README.md` |
| `npx http-server . -p 3001 -a 0.0.0.0` | `uis/backoffice/` | Documented in `uis/backoffice/README.md` (port **3001**) |
| `uv sync` | `services/api/` | Install API + dev deps from lockfile |
| `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` | `services/api/` | Run API (add `--reload` for local dev) |
| `uv run seed` | `services/api/` | Idempotent supplier + demo staff seed |
| `uv run pytest` | `services/api/` | API test suite (`tests/`) |

There is still **no** root lint script and **no** Docker Compose on `main` (containerization remains on an unmerged branch). Do not invent `npm run lint` or assume Compose is available until it lands on `main`.

## What exists on main today (post AUTH PRs)

### `services/api`

- Entry: `app.main:app`
- Health: `GET /health`
- Staff auth: `POST /users`, `POST /auth/login`, `GET /auth/me`, `PUT /profiles/me`, `POST /auth/logout`, `POST /auth/refresh`
- Suppliers: CRUD-style routes under `/suppliers` (Bearer access token required)
- Storage: TinyDB JSON under `services/api/data/` (gitignored runtime data)
- Demo staff after seed: documented in `uis/backoffice/README.md` / API README

### `uis/backoffice`

- Supplier directory UI protected by `js/session.js` (`requireSession`, `apiFetch`, 401 → refresh → redirect to login)
- Pages: `/`, `/login/`, `/register/`, `/account/`, `/account/profile/`
- Default API base: `http://127.0.0.1:8000` (Codespaces and `?api=` overrides supported)

### `uis/website`

- Public static site + Brasa Points form; Tailwind via `npm run build:css`

## Monorepo folder conventions

From the root `README.md`:

- Screens → `uis/`
- API / background → `services/` (this repo uses one FastAPI app at `services/api/`)
- Data → `data/{raw,pipelines,process,eval}`
- Product AI → `agents/`, `skills/`, `mcps/`
- Coding-agent config → `.agents/` and `memory-bank/` (not the same as product `agents/` / `skills/`)
- Shared packages → `packages/`, loose assets → `shared/`
- Docs → `docs/`; deploy → `infra/`; scripts → `scripts/`

## CONTEXT.md resolution

- **Keep the root `CONTEXT.md` already on `main`.** Do not replace it with the narrative rewrite from the old `feature/agent-memory-bank` branch.
- Supplier field names, categories, and statuses live in `Supplier-Directory-CONTEXT.md` (pointed to from `CONTEXT.md`).
- `CONTEXT.es.md` remains a template placeholder unless a task explicitly names it.

## Technical constraints

- Company facts in UI or business docs must come from `CONTEXT.md` / `Supplier-Directory-CONTEXT.md`.
- `npm run typecheck` does not cover `uis/` or `services/`.
- Website and backoffice stay separate apps under `uis/`.
- Protected paths are listed in `AGENTS.md`.

## Open questions (still true)

1. **Package manager vs Dev Container.** Devcontainer enables pnpm/uv; day-to-day lockfiles are npm at root/`uis/website`, and uv for `services/api`.
2. **`apps/` versus `uis/`.** Some package READMEs mention `apps/`; the live tree uses `uis/`.
3. **Docker on main.** Compose artifacts may exist on other branches; they are not part of current `main` until merged.
