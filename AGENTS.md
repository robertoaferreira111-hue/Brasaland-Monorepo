# AGENTS.md

Operating rules for coding agents in the Brasaland monorepo. Company facts come from the root `CONTEXT.md`. Technical facts come from `memory-bank/techContext.md`.

## Read at the start of every session

Read these three files before editing anything:

1. `memory-bank/projectbrief.md`
2. `memory-bank/techContext.md`
3. `memory-bank/progress.md`

Then check any company fact you plan to write against `CONTEXT.md`. If it is not in `CONTEXT.md`, do not write it.

## Mandatory workflow before each commit

Do these steps in order. Do not commit if a step fails.

1. **Confirm scope against `memory-bank/progress.md`.** The change must match the task and the "planned next" or in-progress item you are actually finishing. If the task is not covered there, or it needs a protected path, stop and ask.
2. **Run `npm run typecheck` from the repo root.** The script is `tsc --noEmit`. It covers `src/` only.
3. **If the change touches `uis/website/`, run `npm run build:css` from `uis/website/`.** Skip this step only when no file under `uis/website/` is part of the change. Do not run it from the repo root. That script is not in the root `package.json`.
4. **Update `memory-bank/progress.md`.** Record what this change completed and what is still not done. Do not mark work complete if the command in step 2 or step 3 failed.
5. **Review the diff for unrelated changes.** Stage only files that belong to the task. Leave unrelated deletions and untracked files in `.project_instructions/` unstaged unless the developer explicitly names those files.

## Do not modify without explicit developer confirmation

- `CONTEXT.md`
- Template READMEs, including `README.md` and `README.es.md` files that shipped with the monorepo
- `.project_instructions/`
- Product folders `agents/`, `skills/`, `mcps/`, `workflows/`, `data/`, and `infra/`, unless the task names that folder

`.agents/` is editor configuration. The product trees `agents/` and `skills/` are not the same thing. Do not put coding-agent rules or skills into those product folders.

`CONTEXT.es.md` is still a template placeholder. Do not edit it unless a task names that file.

## When to stop and ask

Stop instead of guessing when any of these are true:

- A company name, number, place, currency, or need is not in `CONTEXT.md`.
- The command you want is not in a `package.json` script and not documented in the folder README. There is no lint script, no test script, and no Docker Compose file. Do not invent one.
- The task would edit a path in the protected list above.
- The task needs a new app under `uis/` other than the existing `uis/website/`. `uis/backoffice/` has no README and no package, so its stack is not defined.
- A README conflict below would change the shape of the change.

### Known README conflicts

Recorded in `memory-bank/techContext.md`. Do not resolve them by editing the READMEs.

- **Services layout.** Root `README.md` describes one centralized FastAPI app under `services/`. `services/README.md` describes one subfolder per service. No service exists yet.
- **`apps/` versus `uis/`.** `packages/README.md` and `shared/README.md` say `apps/`. The root guide and `uis/README.md` say `uis/`. There is no `apps/` directory. UI work goes in `uis/`.
- **Installers.** `.devcontainer/devcontainer.json` prepares pnpm and uv. The lockfiles in the repo are npm `package-lock.json` files, and there is no `pyproject.toml`.
- **Website copy versus the briefing.** `uis/website/README.md` still points form fields and landing-page facts at `CONTEXT.md`. The current briefing does not list those fields. Do not copy website-only details back into `CONTEXT.md` or into new screens as if the briefing stated them.
