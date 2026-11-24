# MCP Server acceptance readiness

Status: **NOT READY — BUSINESS REQUIREMENTS BLOCKED**

Assessed on 20 November 2026 from the working tree on `feat/mcp-company-tools`. This is an assessment. It does not add routes, lifecycle rules, or inventory records.

Operational validation is also incomplete. Live OIDC and MCP Playground were not run. Automated tests passing does not close either gap. No reduced-scope approval is recorded in the assignment, `company-BRIEFING.md`, `CONTEXT.md`, or this repository.

Phase 5.3 adds the procedures and the owner questions. It does not change any status below. Preparation is not execution.

- Live OIDC steps: `docs/mcp/oidc-validation.md`. Status remains pending.
- Playground steps: `docs/mcp/playground-validation.md`. Status remains pending. Evidence belongs in `docs/mcp/evidence/`, which has none.
- Incident write questions: `docs/mcp/incident-lifecycle-decision.md`.
- Inventory read questions: `docs/mcp/inventory-read-decision.md`.

The reference solution is an architectural comparison only. Its routes and sample payloads are not a contract for this repository.

## Decisions

| Gate | Decision |
| --- | --- |
| Technical implementation of the existing read path, auth middleware, write rejection, and LangGraph MCP client | Ready for the behavior the current APIs support |
| Automated regression | Ready on the runs recorded below |
| Operational validation | Not ready. No live issuer and no public Playground URL |
| Original assignment scope | Not complete. Create, status update, and inventory reads have no approved contract |
| Submission | Not ready. No Playground evidence and no pull request |
| `main` completion | Closed. The MCP work is uncommitted. A project is finished only when that work is on `main` |

## Requirement traceability

| Requirement | Status | Evidence |
| --- | --- | --- |
| FastMCP server under `mcps/` | IMPLEMENTED AND TESTED | `mcps/company-tools/company_tools/server.py`. Foundation tests in `tests/test_foundation.py`. Suite: 19 passed on 20 November 2026. |
| MCP Auth on discovery and invocation | IMPLEMENTED — EXTERNAL VALIDATION PENDING | `company_tools/auth.py` uses mcpauth resource-server mode. FastMCP `auth` is unset. Local JWKS tests in `tests/test_auth.py` cover missing, invalid, expired, valid, and insufficient-scope tokens. Startup against a reachable issuer was not demonstrated. On 20 November 2026 the process exited 2 because `MCP_AUTH_*` and the incidents settings were unset. |
| Incident lookup and listing | IMPLEMENTED AND TESTED | `manage_incident_ticket` actions `get_status` and `list` call `GET /api/incidents/{id}` and `GET /api/incidents`. Covered by `tests/test_tools.py` and `tests/pipelines/test_agent_mcp.py`. Not demonstrated in MCP Playground. |
| Incident creation | BLOCKED — MISSING BUSINESS CONTRACT | `services/api/app/routers/incidents.py` registers GET only. `test_openapi_lists_read_routes_only` expects POST `/api/incidents` to return 405. The tool returns `VALIDATION_ERROR` and does not send a write. |
| Incident status update | BLOCKED — MISSING BUSINESS CONTRACT | No status-transition route or approved transition set among `OPEN`, `CLOSED`, and `DISCARDED`. The tool returns `VALIDATION_ERROR` and does not send a write. |
| Inventory product and stock reads | BLOCKED — MISSING BUSINESS CONTRACT | `docs/telemetry/README.md` states the inventory application named in the briefing is not in this repository. `company-BRIEFING.md` does not define a product or stock API. Reads return `VALIDATION_ERROR`. Synthetic telemetry events are not an inventory service. |
| Inventory write protection | IMPLEMENTED AND TESTED | Write actions return `INVENTORY_WRITE_FORBIDDEN` before a scope check and before any HTTP call. Covered by `tests/test_tools.py`. Not demonstrated in Playground. |
| Distinct auth, authorization, and validation errors | IMPLEMENTED AND TESTED | `AUTH_MISSING_TOKEN`, `AUTH_INVALID_TOKEN`, `INSUFFICIENT_SCOPE`, `VALIDATION_ERROR`, and `INVENTORY_WRITE_FORBIDDEN` are separate codes in `company_tools/errors.py` and the auth tests. Local JWKS only. |
| Structured invocation logging | IMPLEMENTED AND TESTED | `company_tools/logging.py` writes one JSON line per call and redacts tokens and sensitive incident fields. `test_secret_redaction` passed in the 19-test run. |
| LangGraph uses MCP for incidents | IMPLEMENTED AND TESTED | `services/agent/nodes.py` `lookup_ticket` calls `services/agent/mcp_incidents.py`. Direct TinyDB incident reads were removed from `services/agent/tools/ticket_lookup.py`. `tests/pipelines/test_agent_mcp.py` passed inside the 40-test run. |
| RAG and conditional routing preserved | IMPLEMENTED AND TESTED | Routing tests and `tests/pipelines/test_agent_evals.py` passed on 20 November 2026, including the grounded eval. 40 passed, 0 skipped. An earlier run the same day had skipped that eval before `.env/local` existed. |
| Streamable HTTP | IMPLEMENTED AND TESTED | `server.py` uses FastMCP `http_app` with `transport="streamable-http"` and path `/mcp`. stdio is rejected by config validation. Public `0.0.0.0` exposure was not exercised. |
| MCP Playground validation | IMPLEMENTED — EXTERNAL VALIDATION PENDING | The server can bind `MCP_HOST`. No Codespaces public URL, Playground session, or screenshot exists. `gh` on this machine lacks the `codespace` scope. |
| Documentation and submission evidence | IMPLEMENTED — EXTERNAL VALIDATION PENDING | `mcps/company-tools/README.md` documents transport, env vars, scopes, errors, and the known limits. A pull request and Playground screenshots are not in the repository. |

`NOT APPLICABLE — EXPLICITLY APPROVED` is unused. Nothing in the assignment was waived.

## Automated test evidence

All counts are from 20 November 2026. Skipped tests are not counted as passed.

| Command | Result |
| --- | --- |
| `REDIS_URL=redis://127.0.0.1:6379/0 uv run pytest` from `services/api` | 169 passed, 0 failed, 0 skipped, 6 Starlette 422 deprecation warnings, 44.93s |
| `uv run --no-sync pytest` from `mcps/company-tools` | 19 passed, 11.78s. Includes local JWKS auth tests. This is not live issuer validation. |
| `services/api/.venv/bin/python -m pytest` on `tests/pipelines/test_agent_mcp.py`, `test_agent_routing.py`, `test_agent_external_tool_evals.py`, `test_ticket_lookup.py`, `test_agent_evals.py`, and `test_rag.py` | 40 passed, 0 skipped, 33.05s. Includes the grounded RAG eval. |

Redis: `docker compose up -d redis flower` reused `brasaland-redis-1` (healthy, created 10 November 2026, volume `brasaland_redis-data`). `redis-cli ping` returned `PONG`. DBSIZE stayed 4. The volume was not removed.

## Operational validation still required

The steps are written in `docs/mcp/oidc-validation.md` and `docs/mcp/playground-validation.md`. They have not been executed. Local JWKS tests do not satisfy them. A Codespace of `origin/main` does not contain this server, because the server is only in the working tree.

1. Set `mcps/company-tools/.env` with `MCP_AUTH_ISSUER`, `MCP_AUTH_AUDIENCE`, `MCP_AUTH_RESOURCE`, `MCP_AUTH_SCOPES`, `MCP_AUTH_INCIDENTS_SCOPE`, `MCP_AUTH_INVENTORY_SCOPE`, `INCIDENTS_API_BASE_URL`, `INCIDENTS_API_TIMEOUT_SECONDS`, and `INCIDENTS_API_TOKEN`. Do not commit that file.
2. The issuer must serve OpenID discovery and a JWKS URI. Start `uv run company-tools` and confirm it stays up.
3. Fetch protected-resource metadata. For a resource URL with a path, the document is `/.well-known/oauth-protected-resource` plus that path.
4. Call `/mcp` with a valid token and confirm tool discovery.
5. Call `manage_incident_ticket` with `incidents.read` and confirm an authorized lookup.
6. Repeat discovery or invocation with a missing token, an invalid token, an expired token, and a token that lacks the tool scope. Expect `AUTH_MISSING_TOKEN`, `AUTH_INVALID_TOKEN`, and `INSUFFICIENT_SCOPE` respectively. Expired tokens use the invalid-token code.
7. Run `gh auth refresh -h github.com -s codespace`, open this repository in Codespaces, set `MCP_HOST=0.0.0.0`, and forward port 8080 as public.
8. In MCP Playground, use `https://<codespace>-8080.app.github.dev/mcp`. Do not substitute localhost.
9. Record discovery, both tool schemas, a real `get_status`, a `list`, and an inventory `update` that returns `INVENTORY_WRITE_FORBIDDEN`.
10. Keep the screenshots under `docs/mcp/evidence/` with the public URL visible. That directory currently contains only a note that no evidence has been added.

`create`, status `update`, and inventory `product` or `stock` calls are expected to return the current rejection messages. Those results are not successful writes or stock lookups.

## Business dependency register

### Incident lifecycle operations

Known:

- `GET /api/incidents` and `GET /api/incidents/{incident_id}` exist. Ids are `BRS-######`. Status filters are `OPEN`, `CLOSED`, and `DISCARDED`. Category filters are `CUSTOMER_COMPLAINT`, `EQUIPMENT`, `SUPPLY`, `FOOD_QUALITY`, and `STAFF`.
- POST `/api/incidents` is 405. The OpenAPI test locks the methods to GET.
- The MCP create and update actions stop before HTTP and return `VALIDATION_ERROR`.
- `company-BRIEFING.md` has no incident contract. The reference solution's POST and status routes are examples, not this API.

Missing:

- Who may create an incident, which fields the client sends, and who assigns `BRS-######`.
- Which transitions among `OPEN`, `CLOSED`, and `DISCARDED` are legal, and what HTTP status an illegal transition uses.
- Approval to change `test_openapi_lists_read_routes_only` if write routes are added.

Unblocks implementation: written answers to `docs/mcp/incident-lifecycle-decision.md`, then a change to `services/api` and the MCP tool. Do not add the routes before that approval.

### Inventory product and stock reads

Known:

- No inventory HTTP API is in this repository. `docs/telemetry/README.md` says the inventory application is not here.
- `INVENTORY_WRITE_FORBIDDEN` is implemented and must stay.
- `data/dev/inventory_seed.py` writes synthetic telemetry events. It is not a product or stock catalog.

Missing:

- The service that owns product and stock data.
- The approved read operations, filters, and response fields.

Unblocks implementation: written answers to `docs/mcp/inventory-read-decision.md`. Do not invent rows or point the tool at telemetry events.

## Evidence still required

- Live issuer startup log with secrets removed.
- Protected-resource metadata response.
- Live results for a valid token and for missing, invalid, expired, and insufficient-scope tokens.
- The public Codespaces URL actually used.
- Playground screenshots for discovery, schemas, incident lookup, incident list, and inventory write rejection.
- Owner approval of the incident write contract, or a written decision that those assignment items are out of scope.
- Owner identification of the inventory read API, or a written decision that those items are out of scope.
- An authorized commit and pull request after the above. None of that is authorized now.

## Git

Reverified read-only on 20 November 2026 during Phase 5.3:

- Branch `feat/mcp-company-tools`
- `HEAD`, `main`, and `origin/main`: `f1deca8111f25793ec7eec3806b17cad329e8944`
- `git rev-list --left-right --count origin/main...HEAD`: `0 0`

Those three refs matching does not mean the MCP work is merged. `git ls-files` does not track `mcps/company-tools/company_tools/server.py` or `docs/mcp/oidc-validation.md`. The server and these documents are uncommitted working-tree files. `.env/local` remains ignored.

Modified tracked files include `.env.example`, `.gitignore`, the agent incident path, `services/api/pyproject.toml`, `services/api/uv.lock`, and the agent tests that now use MCP. Untracked files include `mcps/company-tools/`, `services/agent/mcp_incidents.py`, `tests/pipelines/mcp_stack.py`, `tests/pipelines/test_agent_mcp.py`, and `docs/mcp/`.

No checkout, commit, push, pull request, merge, reset, or rebase was made.

## Next phase

Do not start an implementation phase yet. Phase 5.3 did not add routes, change tool schemas, or mark any requirement not applicable.

1. User action: follow `docs/mcp/oidc-validation.md` and store redacted output in `docs/mcp/evidence/`.
2. User action: authorize a Git write so a Codespace can see this working tree, then follow `docs/mcp/playground-validation.md`. A Codespace of `origin/main` does not contain the server.
3. Project-owner action: answer `docs/mcp/incident-lifecycle-decision.md` and `docs/mcp/inventory-read-decision.md`, or explicitly defer those assignment items in writing.
4. Implementation phase only after step 3 names the contract. That phase may add the approved routes and then point the existing MCP tools at them. It does not invent fields.
5. Submission phase only after the user authorizes Git writes. The pull request must not claim create, status update, inventory reads, live OIDC, or Playground unless that evidence exists.
