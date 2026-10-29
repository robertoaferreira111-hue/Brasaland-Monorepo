# AGENTS.md

Operating rules for coding agents in the Brasaland monorepo. Company facts come from the root `CONTEXT.md` (and `Supplier-Directory-CONTEXT.md` for supplier schema). Technical facts come from `memory-bank/techContext.md`.

## Read at the start of every session

Read these three files before editing anything:

1. `memory-bank/projectbrief.md`
2. `memory-bank/techContext.md`
3. `memory-bank/progress.md`

Then check any company fact you plan to write against `CONTEXT.md` / `Supplier-Directory-CONTEXT.md`. If it is not there, do not write it.

## Mandatory workflow before each commit

Do these steps in order. Do not commit if a step fails.

1. **Confirm scope against `memory-bank/progress.md`.** The change must match the task you are finishing. If it needs a protected path, stop and ask.
2. **Run `npm run typecheck` from the repo root** when the change touches `src/` or root TypeScript config. The script is `tsc --noEmit` and covers `src/` only.
3. **If the change touches `uis/website/`, run `npm run build:css` from `uis/website/`.**
4. **If the change touches `services/api/`, run `uv run pytest` from `services/api/`** (after `uv sync` if deps changed).
5. **Update `memory-bank/progress.md`** when the change finishes a tracked milestone or integration stage.
6. **Review the diff for unrelated changes.** Stage only files that belong to the task.

## Do not modify without explicit developer confirmation

- `CONTEXT.md` and `Supplier-Directory-CONTEXT.md` (unless the task explicitly asks to update domain facts)
- Template READMEs that shipped with the monorepo (`README.md` / `README.es.md` at root and many folders)
- `.project_instructions/`
- Product folders `agents/`, `skills/`, `mcps/`, `workflows/`, `data/`, and `infra/`, unless the task names that folder

`.agents/` is coding-agent configuration. The product trees `agents/` and `skills/` are not the same thing.

`CONTEXT.es.md` is still a template placeholder. Do not edit it unless a task names that file.

## When to stop and ask

Stop instead of guessing when any of these are true:

- A company name, number, place, currency, or need is not in `CONTEXT.md` / `Supplier-Directory-CONTEXT.md`.
- The command you want is not in a `package.json` / `pyproject.toml` script and not documented in the folder README.
- The task would edit a path in the protected list above.
- The task would introduce a second auth stack instead of extending `services/api` + `uis/backoffice` session flows already on `main`.

### Known README conflicts

Recorded in `memory-bank/techContext.md`. Do not resolve them by editing the READMEs unless asked.

- **Services layout.** Root `README.md` prefers one centralized FastAPI app. `services/README.md` still reads like one-folder-per-service. Current code uses `services/api/`.
- **`apps/` versus `uis/`.** Some package READMEs say `apps/`. Live tree uses `uis/`.
- **Installers.** Devcontainer prepares pnpm and uv; root/`uis/website` use npm lockfiles; API uses uv.
