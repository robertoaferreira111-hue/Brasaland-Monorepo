# Technical context

Facts in this file were checked against the repository. Company facts belong in `CONTEXT.md` and `memory-bank/projectbrief.md`. If a command or path is not listed here, do not invent it.

## Stack that is declared

There is no root workspace file and no `workspaces` field in the root `package.json`. Each manifest stands alone. Lockfiles are npm `package-lock.json` files (lockfileVersion 3): one at the repo root, one in `uis/website/`, and one in `uis/backoffice/`.

| Location | Declared stack |
| --- | --- |
| Repo root, package name `brasaland-operations` | TypeScript `^5.8.2` and `tsx` `^4.19.3`, both devDependencies. Description in `package.json`: operations data-processing utilities (Milestone 2). |
| `tsconfig.json` | Target `ES2022`, `module` `ESNext`, `strict` true, `noEmit` true, `rootDir` `src`, `include` `src/**/*.ts`. `exclude` lists `node_modules`, `dist`, `uis`, `packages`, `agents`, and `skills`. |
| `uis/website`, package name `brasaland-website` | Static HTML. The only devDependency is `tailwindcss` `3.4.17`. `uis/website/README.md` says pages use Tailwind utility classes in precompiled `styles.css` and do not load the Tailwind browser runtime. |
| `uis/backoffice`, package name `brasaland-backoffice` | Same approach as the public site: static HTML, Tailwind utility classes compiled to this folder's own `styles.css`. The only devDependency is `tailwindcss` `3.4.17`. See "Backoffice stack choice" below. |
| `packages/shared/package.json` | Package name `@repo/shared-types`. `main` and `types` point at `index.ts`. `scripts` is empty. |
| `.devcontainer/devcontainer.json` | Image `mcr.microsoft.com/devcontainers/base:ubuntu-24.04`. Features request Python 3.12 and Node 22. Forwarded ports are 3000, 8000, and 5678. |

`services/` has a README and no service package. The backoffice entry view does not call an API, so no service was added. `agents/_template/agent.py` is empty. No `pyproject.toml`, `docker-compose.yml`, ESLint config, or Prettier config is in the repo.

## Commands that exist

Run each command from the directory that owns the script.

| Command | Where | Source |
| --- | --- | --- |
| `npm run typecheck` | Repo root | `package.json` script: `tsc --noEmit`. It typechecks `src/` only, because `tsconfig.json` excludes `uis`. |
| `npm run demo` | Repo root | `package.json` script: `node --import tsx src/demo.ts`. |
| `npm run build:css` | `uis/website/` | `uis/website/package.json` script: `tailwindcss -i ./tailwind.css -o ./styles.css --minify`. `uis/website/README.md` says this is dev-time only and that serving the site does not run it. The same README documents `npm install` in that folder before the build. |
| `npx http-server . -p 3000 -a 0.0.0.0` | `uis/website/` | Documented in `uis/website/README.md` and `uis/README.md`. Open `http://127.0.0.1:3000`. `http-server` is not a dependency in `uis/website/package.json`. |
| `npm run build:css` | `uis/backoffice/` | `uis/backoffice/package.json` script: `tailwindcss -i ./tailwind.css -o ./styles.css --minify`. `uis/backoffice/README.md` says to run `npm install` in that folder first, and that serving does not run the build. |
| `npx http-server . -p 3010 -a 0.0.0.0` | `uis/backoffice/` | Documented in `uis/backoffice/README.md`. Open `http://127.0.0.1:3010`. Port 3010 is documented there so this app does not take the public site's port 3000. `http-server` is not a dependency in `uis/backoffice/package.json`. |

No lint command exists. No test command exists. Do not invent `npm run lint`, `npm test`, a formatter script, or a Docker Compose command.

## Monorepo folder conventions

From the root `README.md` decision guide:

- Screens and buttons go in `uis/`. The public site is `uis/website/`. The internal app is supposed to be `uis/backoffice/`. `uis/README.md` says each subfolder is a separate concern with its own documentation.
- An API or background process goes in `services/`.
- Raw data, pipelines, processed outputs, and evaluation sets go in `data/raw/`, `data/pipelines/`, `data/process/`, and `data/eval/`.
- An AI assistant with a goal goes in `agents/`. Reusable agent capabilities for the product go in `skills/`. Live tool servers go in `mcps/`.
- Scheduled or n8n-style automation goes in `workflows/`.
- Code imported by more than one app goes in `packages/`. Schemas and loose assets go in `shared/`.
- Architecture docs go in `docs/`. Deploy config goes in `infra/`. One-off scripts go in `scripts/`. A CLI with its own package goes in `internal/`.

`.agents/` is the coding-agent configuration directory (rules and skills for the editor). It is not the product `agents/` or `skills/` tree.

`uis/website/README.md` conventions for that app: static HTML, Tailwind utility classes, `validation.js`, English as the base language, and company facts taken from the root `CONTEXT.md`. `tailwind.config.js` scans `index.html` and `application.html`.

## Backoffice stack choice

`uis/README.md` names `backoffice/` as the internal app and says each UI subfolder documents its own technology. It does not name a framework. `uis/website` is the sibling app and is static HTML plus Tailwind 3.4.17 compiled to a local `styles.css`, served with `npx http-server`. No README tells the backoffice to use a different stack, so `uis/backoffice` uses that same approach.

The layout is not shared. `uis/backoffice/index.html` is an internal desk: a zinc sidebar and a main column. It does not import `uis/website` HTML, CSS, images, or scripts. Its Tailwind config scans only `uis/backoffice/index.html`. The public site stays stone and orange with a top navigation bar.

No service was added. The entry view renders company facts from `CONTEXT.md` in the HTML. It does not need an API. The root README's "one FastAPI app" guidance and `services/README.md`'s "one folder per service" guidance still disagree, and creating an unused service would have required choosing one of them.

## Technical constraints

- Company facts used in UI or docs written for the business must come from `CONTEXT.md`. The briefing does not list individual restaurant names, a 10/4 country split, menu items, prices, phone numbers, or form fields.
- `npm run typecheck` does not cover `uis/`, `packages/`, `agents/`, or `skills/`.
- The website and the backoffice stay separate apps under `uis/`. Do not share a layout between them.
- Protected paths are listed in `AGENTS.md`. Do not edit them without explicit developer confirmation.
- `CONTEXT.es.md` is still the Spanish template placeholder. It is not the briefing. This phase does not edit it.

## Open questions

These conflicts are in the repo and are not resolved here.

1. **Package manager.** In `.devcontainer/devcontainer.json`, the `js` entry of `postCreateCommand` enables pnpm and runs `pnpm install` when a `package.json` exists. The `python` entry installs uv and runs `uv sync` when `pyproject.toml` exists. The repo has npm lockfiles and no `pyproject.toml`. Which installer to use for day-to-day work is not settled.
2. **Service layout.** The root `README.md` says `services/` is one centralized FastAPI app (for example `api/`) and that microservices should be avoided early. `services/README.md` says each subfolder is one specific service (examples given: `admin-api`, `data-processor-worker`). No service has been created. Do not pick a layout until this is decided.
3. **`apps/` versus `uis/`.** `packages/README.md` and `shared/README.md` mention an `apps/` directory. The root `README.md` and `uis/README.md` use `uis/`. There is no `apps/` folder.
4. **Website README versus the current briefing.** `uis/website/README.md` says landing-page facts, field order, and messages come from the root `CONTEXT.md`, and it documents `index.html`, `application.html`, and Restaurant JSON-LD. The briefing now in `CONTEXT.md` does not specify those form fields or that markup. Do not treat the existing website copy as a new business source.
