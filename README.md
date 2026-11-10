# AI Engineering Company Project — Student Template

[![4Geeks Academy](https://img.shields.io/badge/4Geeks-Academy-blue)](https://4geeksacademy.com)
[![AI Engineering](https://img.shields.io/badge/track-AI%20Engineering-green)](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)

_Base template for transversal projects in the AI Engineering Career Program — 4Geeks Academy._

_Estas instrucciones tambien estan disponibles en [espanol](./README.es.md)._

---

## Purpose

This repository is the **starter template** for transversal projects. You will work on real company scenarios (Brasaland, TrackFlow, Nexova), building deliverables that map to course milestones (Web, Programming, Backend, Telemetry, RAG, Agents, Workflows, Real-time).

- Create a template from this repository.
- Replace the placeholder `CONTEXT.md` with your assigned company context.
- Use `skills/` and the directory-level `README.md` files as working guidance.

---

## How to start

1. **Use this repository as a template** and create your own project repo.
2. **Clone** your repository (or open it in Codespaces).
3. **Replace** `CONTEXT.md` with the full context for your assigned company.
4. **Read this folder guide** and open the `README.md` of the folder you are working in.
5. **Start implementing** in the right folder — do not dump everything in the root.
6. **Document** what you add: each new app, service, agent, or pipeline gets a subfolder + README.

---

## How to think about this monorepo

You are building **one company** across many milestones and projects. Each top-level folder has a **single responsibility** — like a real engineering team repo.

| Layer               | Folders                           | What lives here                                                  |
| ------------------- | --------------------------------- | ---------------------------------------------------------------- |
| **Company context** | `CONTEXT.md`                      | Domain facts, field names, constraints for your assigned company |
| **User-facing**     | `uis/`, `services/`               | Frontends and backends users (or operators) interact with        |
| **Data**            | `data/`                           | Raw files, pipelines, processed datasets, evaluation sets        |
| **AI**              | `agents/`, `skills/`, `mcps/`     | Agents, reusable agent capabilities, MCP tool servers            |
| **Automation**      | `workflows/`                      | n8n flows and cross-system orchestration                         |
| **Reuse**           | `packages/`, `shared/`            | Shared types, SDKs, schemas, templates                           |
| **Operations**      | `infra/`, `scripts/`, `internal/` | Docker, deploy configs, one-off scripts, internal CLIs           |
| **Documentation**   | `docs/`                           | Architecture, decisions, conventions for the whole repo          |

**Rule of thumb:** if it has a UI → `uis/`. If it exposes an API or runs in the background → `services/`. If it moves or transforms data → `data/`. If an AI model does the work → `agents/` (+ `skills/` or `mcps/` as needed).

---

## Current status of the template

> 💡 This repository currently provides a **base folder structure and documentation skeleton** only. It does not include runnable apps or global scripts yet.
>
> - `CONTEXT.md` is a placeholder and must be replaced with your assigned company context.
> - There is no root `AGENTS.md` yet.
> - Shared package metadata exists in `packages/shared/package.json` (`@repo/shared-types`), but no workspace runner is configured at root.

---

## Folder guide — what goes where

Read the linked `README.md` inside each folder before you start coding there.

### Root files

| Path                         | Purpose                                                                   | What you do here                                                                                              |
| ---------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| [`CONTEXT.md`](./CONTEXT.md) | Single source of truth for your company (Brasaland, TrackFlow, or Nexova) | **First step:** copy your assigned company briefing here so every app, agent, and prompt uses the same domain |
| `docker-compose.yml`         | Local dev orchestration for the whole stack                               | Keep at repo root — wires `services/`, databases, and other containers from one place                         |
| `README.md` / `README.es.md` | This guide                                                                | Orientation — you are here                                                                                    |

### `uis/` — user interfaces

**Purpose:** All frontend applications — anything a human sees and clicks.

**Put here:**

- Public website (`website/`)
- Internal admin / backoffice (`backoffice/`)
- Customer portals, loyalty apps, Streamlit/Gradio tools, dashboards with a UI

**Examples:** corporate landing page, operations backoffice, loyalty portal, telemetry dashboard UI

→ See [`uis/README.md`](./uis/README.md)

### `services/` — centralized company API (FastAPI)

**Purpose:** One **centralized FastAPI backend** for the whole company — a single entry point that keeps complexity low as the project grows.

**Put here:**

- One main FastAPI app (e.g. `api/`) with routers/modules per domain (locations, menus, sales, telemetry, etc.)
- Background workers only when they truly need to run separately from the API

**Recommendation:** avoid splitting into many microservices early. Add endpoints to the same FastAPI app; extract a worker only when necessary.

**Examples:** `/locations`, `/menus`, `/sales/reports`, webhook handlers, scheduled jobs

→ See [`services/README.md`](./services/README.md)

### `data/` — datasets, pipelines, and evaluation

**Purpose:** Everything data-related, from raw files to production-ready tables.

| Subfolder                                       | Purpose                      | What you do here                                                          |
| ----------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------- |
| [`data/raw/`](./data/raw/README.md)             | Untouched source data        | Store dumps, exports, sample CSVs/JSON — document origin and PII rules    |
| [`data/pipelines/`](./data/pipelines/README.md) | ETL/ELT jobs                 | Write ingestion, cleaning, and transformation scripts                     |
| [`data/process/`](./data/process/README.md)     | Clean / intermediate outputs | Save artifacts produced by pipelines (features, aggregates, clean tables) |
| [`data/eval/`](./data/eval/README.md)           | Quality measurement          | Golden sets, RAG/agent eval datasets, experiment metrics                  |

**Flow:** `raw` → `pipelines` → `process` → consumed by `services/`, `uis/`, or `agents/`. Use `eval` to prove quality.

### `agents/` — AI agents

**Purpose:** Autonomous or semi-autonomous AI assistants for the company.

**Put here:**

- One subfolder per agent (e.g. `support-agent/`, `onboarding-agent/`)
- Agent config, prompts, tools wiring, tests
- Start from [`agents/_template/`](./agents/_template/README.md) when creating a new agent

**Examples:** customer support bot, employee onboarding copilot, training assistant

→ See [`agents/README.md`](./agents/README.md)

### `skills/` — reusable agent capabilities

**Purpose:** Packaged instructions + scripts that agents (or you in Cursor) reuse across the repo.

**Put here:**

- Skills for data analysis, code review, scraping, research, etc.
- Each skill = a folder with `SKILL.md`, optional scripts and resources

**Example included:** `skills/data-analysis/` (pandas cleaning script + metrics reference)

→ See [`skills/README.md`](./skills/README.md)

### `mcps/` — Model Context Protocol servers

**Purpose:** Bridge AI models to your systems — databases, APIs, GitHub, custom tools.

**Put here:**

- One subfolder per MCP server (e.g. `database-mcp/`, `github-mcp/`)
- Tool definitions, resources, and server config

**When to use:** when an agent needs live access to data or actions your codebase alone cannot provide

→ See [`mcps/README.md`](./mcps/README.md)

### `workflows/` — automation and orchestration

**Purpose:** Connect systems without writing full apps — scheduled jobs, webhooks, notifications.

**Put here:**

- n8n workflow exports, Make/Zapier configs, or orchestration docs
- Flows that link `services/`, `data/pipelines/`, and `agents/`

**Examples:** new-order → Slack alert, nightly ETL trigger, lead → CRM sync

→ See [`workflows/README.md`](./workflows/README.md)

### `packages/` — shared libraries

**Purpose:** Versionable code reused by multiple apps, agents, or pipelines.

**Put here:**

- Shared TypeScript types (`packages/shared/` → `@repo/shared-types`)
- UI component libraries, API clients, analytics SDKs

**Rule:** if `uis/` and `services/` both need the same interface → extract it here

→ See [`packages/README.md`](./packages/README.md)

### `shared/` — loose shared assets

**Purpose:** Resources that are not a full package — schemas, templates, static assets, short docs.

**Put here:**

- JSON schemas, email templates, OpenAPI specs, design tokens
- Anything reused but too small or non-code for `packages/`

→ See [`shared/README.md`](./shared/README.md)

### `docs/` — cross-cutting documentation

**Purpose:** Architecture and decisions that span the whole company project.

**Put here:**

- System architecture diagrams, ADRs, security/observability guides
- Conventions not tied to one app or agent

→ See [`docs/README.md`](./docs/README.md)

### `infra/` — infrastructure and deployment

**Purpose:** How the company project runs in Docker, cloud, or CI.

**Put here:**

- Dockerfiles, Terraform, K8s manifests, Nginx configs, CI/CD pipelines

**Keep at repo root:** `docker-compose.yml` — orchestrates local dev for `services/`, databases, and other containers from one place.

→ See [`infra/README.md`](./infra/README.md)

### `scripts/` — helper scripts

**Purpose:** Small, repeatable automation — not full apps.

**Put here:**

- Setup scripts, seed data generators, lint wrappers, one-off migrations
- Document each script: what it does, args, and how to run it

**Difference from `internal/`:** scripts are usually single files; `internal/` tools are structured projects with their own deps and tests.

→ See [`scripts/README.md`](./scripts/README.md)

### `internal/` — internal developer tools

**Purpose:** Robust utilities for the engineering team.

**Put here:**

- CLIs, packaged migration tools, prompt evaluators
- Tools with their own `package.json`, tests, and install steps

→ See [`internal/README.md`](./internal/README.md)

---

## Where should I put this?

Quick decision guide:

```text
Does it have buttons and screens?          → uis/
Does it run on a server / API / queue?     → services/
Is it raw or transformed data?             → data/raw/ or data/process/
Does it move data between systems?         → data/pipelines/
Do you measure AI/pipeline quality?        → data/eval/
Is it an AI assistant with a goal?         → agents/
Is it a reusable AI capability/instruction?→ skills/
Does AI need to call external tools/APIs?  → mcps/
Is it n8n / scheduled automation?          → workflows/
Will 2+ folders import the same code?      → packages/
Is it a schema/template/asset, not a lib?  → shared/
Is it architecture or team-wide docs?      → docs/
Is it docker-compose for local dev?        → repo root
Is it Docker / deploy / cloud config?      → infra/
Is it a one-off script?                    → scripts/
Is it a CLI tool with its own package?     → internal/
```

---

## Repository structure (tree)

```text
ai-engineering-company-project-monorepo/
├── README.md / README.es.md   # This guide
├── CONTEXT.md                 # ← Replace with your company briefing
├── docker-compose.yml         # ← Local dev orchestration (repo root)
├── uis/                       # Frontends (website, backoffice, dashboards)
├── services/                  # Centralized FastAPI company API
├── data/
│   ├── raw/                   # Source datasets
│   ├── pipelines/             # ETL/ELT jobs
│   ├── process/               # Clean / intermediate outputs
│   └── eval/                  # Evaluation sets and metrics
├── agents/                    # AI agents (+ _template/ starter)
├── skills/                    # Reusable agent skills
├── mcps/                      # MCP servers for tool access
├── workflows/                 # n8n and automation flows
├── packages/                  # Shared libraries (@repo/shared-types, …)
├── shared/                    # Schemas, templates, loose assets
├── docs/                      # Architecture and cross-cutting docs
├── infra/                     # Docker, Terraform, deployment
├── scripts/                   # Helper scripts
└── internal/                  # Internal CLIs and dev tools
```

---

## Async task queue

The weekly pipeline trigger does not run the ETL inside the API process. `POST /reporting/pipeline-runs` checks for a live lease, publishes `app.tasks.run_weekly_pipeline` to Redis, and returns `202` with `{"task_id": "..."}`. A separate Celery worker, started from `services/api`, runs `execute_flow`. Redis is the broker and the result backend. Flower reads the same broker for the monitor at [http://127.0.0.1:5555](http://127.0.0.1:5555).

Stopping the API does not stop the worker and does not remove messages already in Redis. A task queued while the worker is down stays in the queue and runs after the worker starts.

### Environment

Copy the example file to the gitignored root `.env` (`cp .env.example .env`). Do not commit that file.

| Variable | Role |
| --- | --- |
| `REDIS_URL` | Broker and result backend. Host API and worker: `redis://localhost:6379/0`. Processes inside Compose use `redis://redis:6379/0`. DB index 0 is the queue. |
| `DATABASE_URL` | Postgres used by the pipeline and by `public.dlq_tasks`. Set it in the root `.env`. The example file shows the shape; keep the real value local. |

The API and the worker load the root `.env` themselves. A staff Bearer token is required on the reporting and task routes. `uv run seed` from `services/api` creates the local demo account when it is missing.

### Start and stop

Redis and Flower, from the repository root:

```bash
docker compose up -d redis flower
docker compose stop redis flower
```

Postgres for this repo is the existing container `brasaland-dev-postgres` (database `brasaland`). It is not one of the Compose services above.

API, from `services/api`:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Worker, from `services/api`, in its own terminal:

```bash
uv run celery -A app.celery_app worker --loglevel=info
```

Stop each process with Ctrl-C in the terminal that started it.

### HTTP contract

`POST /reporting/pipeline-runs` with a staff token:

- `202` `{"task_id": "..."}` when the task is queued. The body has no `run_id`.
- `409` when a run already holds a live lease. `detail.active_run_id` is that run. `detail.code` is `pipeline_run_in_progress`.
- `503` `{"detail": "Queue unavailable"}` when Redis cannot accept the publish.
- `401` `{"detail": "Not authenticated"}` when the token is missing or invalid.

`GET /tasks/{task_id}` uses the same staff token and returns `task_id`, `status`, and `result`. `status` is `pending`, `started`, `success`, or `failure`. Celery `RETRY` is `started`. Celery `REVOKED` is `failure`. An id Celery does not know is `pending` with `result` null.

```json
{"task_id": "2f25c7da-7957-4136-9324-33a878482d45", "status": "pending", "result": null}
```

```json
{"task_id": "2f25c7da-7957-4136-9324-33a878482d45", "status": "started", "result": null}
```

```json
{"task_id": "2f25c7da-7957-4136-9324-33a878482d45", "status": "success", "result": {"run_id": "ebc723cd-64b5-4909-aade-d108b573d086", "status": "success"}}
```

```json
{"task_id": "026ccb89-a416-4771-83ac-c4f40f767b09", "status": "failure", "result": "BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST is set"}
```

`run_id` is created by the worker. After success it is in `result.run_id` and in `GET /reporting/pipeline-runs/latest`.

### Dead letter and the test switch

The worker retries a failed task three times, waiting 10s, then 20s, then 40s. The exhausted task is one row in `public.dlq_tasks`. Host `psql` is not required:

```bash
docker exec brasaland-dev-postgres psql -U postgres -d brasaland -c "select task_id, task_name, attempt, error_message, created_at from public.dlq_tasks order by created_at desc;"
```

`BRASALAND_PIPELINE_TASK_FAIL_FOR_TEST` forces the task to fail before the ETL. It is off unless that variable is set in the worker process environment (`1`, `true`, `yes`, or `on`). Do not put it in a committed file or in `.env`.

If the worker is hard-killed, a `reporting.pipeline_runs` row can stay `running` until its 15-minute lease expires. A retry in that window raises `PipelineLeaseHeld` and the task ends in the dead-letter table.

---

## Links

- [4Geeks Academy — AI Engineering](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia)
- [How to start a coding project](https://4geeks.com/lesson/how-to-start-a-project)

---

## Contributors

This template was built as part of the 4Geeks Academy AI Engineering Career Program by [@marcogonzalo](https://www.linkedin.com/in/marcogonzalo) and [@alesanchezr](https://x.com/alesanchezr) and many other contributors. Find out more about our [AI Engineering Course](https://4geeksacademy.com/en/career-programs/ai-engineering), and [other courses](https://4geeksacademy.com/en/program-comparison).

You can find other templates and resources like this at the [4Geeks Academy GitHub page](https://github.com/4geeksacademy).

_This template is maintained by 4Geeks Academy for the AI Engineering track. For exclusive use in the programme._
