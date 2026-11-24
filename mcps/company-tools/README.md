# Brasaland company tools

MCP server for the Brasaland monorepo. It exposes the live incidents API and a read-only inventory tool. The support agent in `services/agent` is the only incident path, and it calls this server through `langchain-mcp-adapters`.

Python 3.12. Own uv project: `pyproject.toml` and `uv.lock`. The package is `company_tools` so `logging.py` does not replace the standard library.

## Dependencies

From `mcps/company-tools`:

```bash
uv sync
```

Runtime: `fastmcp`, `mcpauth==0.2.0b1`, `httpx`, `uvicorn`, `python-dotenv`, and `cryptography` pinned below 43 so Intel macOS can use a wheel. Tests use `pytest`.

The support agent adds `langchain-mcp-adapters` to `services/api`. FastMCP built-in OAuth is not used.

## Transport

Streamable HTTP, stateless, endpoint `/mcp`.

stdio is not started. MCP Playground has to reach a public URL, and protected-resource metadata is an HTTP route. A subprocess stdio server cannot serve either. `MCP_HOST` and `MCP_PORT` default to `127.0.0.1` and `8080`. In GitHub Codespaces set `MCP_HOST=0.0.0.0` and forward port `8080` with public visibility. The Playground address is that forwarded URL plus `/mcp`. A localhost URL is not an external address.

## Environment

Copy `.env.example` to `.env` in this directory. `uv run company-tools` loads `.env` without overriding variables that are already set. Do not commit `.env`.

| Variable | Required | Role |
| --- | --- | --- |
| `MCP_TRANSPORT` | no | Must be `streamable-http` when set |
| `MCP_HOST` | no | Bind address. `0.0.0.0` in Codespaces |
| `MCP_PORT` | no | Default `8080` |
| `INCIDENTS_API_BASE_URL` | yes | Live incidents API origin |
| `INCIDENTS_API_TIMEOUT_SECONDS` | yes | Positive timeout for every incidents call |
| `INCIDENTS_API_TOKEN` | yes | Staff access token sent only to the incidents API |
| `MCP_AUTH_ISSUER` | yes | OIDC issuer. Startup calls `fetch_server_config` |
| `MCP_AUTH_AUDIENCE` | yes | JWT `aud` |
| `MCP_AUTH_RESOURCE` | yes | Protected-resource identifier |
| `MCP_AUTH_SCOPES` | yes | Comma-separated scopes advertised in metadata |
| `MCP_AUTH_INCIDENTS_SCOPE` | yes | Scope for `manage_incident_ticket`. Must be one of `MCP_AUTH_SCOPES` |
| `MCP_AUTH_INVENTORY_SCOPE` | yes | Scope for `query_inventory`. Must be a different member of `MCP_AUTH_SCOPES` |
| `INVENTORY_API_BASE_URL` | no | Stored only. This repository has no inventory HTTP route, so it is not called |
| `INVENTORY_API_TIMEOUT_SECONDS` | when the inventory URL is set | Positive timeout |

The agent, in the API process, uses:

| Variable | Role |
| --- | --- |
| `MCP_SERVER_URL` | Server URL including `/mcp` |
| `MCP_ACCESS_TOKEN` | OAuth access token for this MCP server. It is not `INCIDENTS_API_TOKEN` |
| `MCP_CLIENT_TIMEOUT_SECONDS` | Client timeout. Default 15 |

There is no OIDC issuer in this repository. The server does not stay up until `MCP_AUTH_ISSUER` answers discovery and publishes a JWKS URI.

## Authentication and scopes

mcpauth 0.2 runs in resource-server mode.

- `fetch_server_config` loads the issuer at startup.
- Protected resource metadata is public. For a resource URL with a path, the document is `/.well-known/oauth-protected-resource` plus that path.
- `bearer_auth_middleware("jwt", resource=..., audience=...)` protects `/mcp` before discovery and invocation. It checks the issuer JWKS, expiry, audience, and the resource's authorization server.
- `MCP_AUTH_INCIDENTS_SCOPE` is the only scope `manage_incident_ticket` accepts. `MCP_AUTH_INVENTORY_SCOPE` is the only scope `query_inventory` accepts. Discovery does not require both.

`GET /health` is public. It reports `status`, `transport`, `auth` (`mcpauth`), and `resource`. `INCIDENTS_API_TOKEN` is not returned to MCP clients and is not written to invocation logs.

## Startup

From `mcps/company-tools`, with the variables above set:

```bash
uv run company-tools
```

Missing or invalid configuration, or a failed issuer fetch, exits 2.

## Agent connection

The graph node `lookup_ticket` is unchanged in position. Its body opens one Streamable HTTP session, loads tools with `langchain-mcp-adapters`, calls `manage_incident_ticket`, and closes the session. Set `MCP_SERVER_URL` and `MCP_ACCESS_TOKEN` on the API process. The token needs `MCP_AUTH_INCIDENTS_SCOPE`. A normal question still routes the same way: manuals, the incident tool, or both, with the tool first when both apply.

`incident_action` `create` or `update` on a graph input sends that action through the same node. The HTTP route `POST /agent/query` only sends the question, so those actions are not inferred from prose.

## Tools

`manage_incident_ticket`

- `action`: `list`, `get_status`, `create`, or `update`
- `ticket_id`: `BRS-######`, required for `get_status` and `update`
- `status`: `OPEN`, `CLOSED`, or `DISCARDED`. List filter, or the target status for `update`
- `category`: `CUSTOMER_COMPLAINT`, `EQUIPMENT`, `SUPPLY`, `FOOD_QUALITY`, or `STAFF`. List filter

`get_status` sends `GET /api/incidents/{ticket_id}` and returns that JSON record. `list` sends `GET /api/incidents` with the filters that match those enums. A bad id, status, or category is `VALIDATION_ERROR` and is not sent.

`query_inventory`

- `action`: `product` or `stock`. `update`, `create`, `delete`, `write`, `set`, and `adjust` are writes
- `product_id`: required for `product` and `stock`
- `quantity` and `stock`: any value is a write

## Error codes

| Code | When | What the client sees |
| --- | --- | --- |
| `AUTH_MISSING_TOKEN` | No bearer token | HTTP 401. "An OAuth access token is required." |
| `AUTH_INVALID_TOKEN` | Invalid or expired token | HTTP 401. "The OAuth access token is invalid or expired." |
| `INSUFFICIENT_SCOPE` | Token lacks the tool scope | Tool result. "The access token does not include the scope required for this operation." |
| `INVENTORY_WRITE_FORBIDDEN` | Inventory write action or `quantity` / `stock` | Tool result. "Inventory tool is read-only. Write operations are not permitted on this MCP server." |
| `VALIDATION_ERROR` | Bad tool input, incident create, incident update, or an inventory read | Tool result. Create: "The incidents API exposes read routes only. Create was not sent." Update: "The incidents API has no status-update route. The requested transition was not sent." Inventory read: "This repository has no inventory HTTP route." |
| `UPSTREAM_ERROR` | Incidents timeout, connection failure, or HTTP error | Tool result. `404` is "Incident not found". `401` and `403` say the service credential was rejected and omit the token. |

Authentication failures stay on HTTP 401. A missing scope is not an authentication failure.

Each tool call logs one JSON line on `company_tools.invocation`: `timestamp` (UTC), `client_id`, `tool`, `input_summary`, `result` (`success` or `failure`), `error_code`, and `duration_ms`. Tokens, secrets, and sensitive incident fields such as `description` and `customer_id` are replaced with `[redacted]`.

## Tests

MCP server, from `mcps/company-tools`:

```bash
uv run pytest
```

Agent, routing, and RAG, from the repository root, with the `services/api` environment:

```bash
services/api/.venv/bin/python -m pytest \
  tests/pipelines/test_agent_mcp.py \
  tests/pipelines/test_agent_routing.py \
  tests/pipelines/test_agent_external_tool_evals.py \
  tests/pipelines/test_ticket_lookup.py \
  tests/pipelines/test_agent_evals.py \
  tests/pipelines/test_rag.py
```

The agent tests start a local incidents app, a local OIDC issuer, and this server. They do not use the full API process, because that process requires `REDIS_URL`.

Verified on 20 November 2026: company-tools `19 passed`. Agent, routing, and RAG `39 passed, 1 skipped`. The skip is the grounded RAG eval. The test records that the skip is not a pass. It runs only when `EMBEDDING_MODEL`, `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, and `GENERATION_MODEL` are set. No root `.env` is present, so those credentials are unset.

On 20 November 2026 the Docker daemon was started locally and `docker compose up -d redis flower` reused the existing `brasaland-redis-1` container. `redis-cli ping` returned `PONG`. The volume was not removed. `REDIS_URL=redis://127.0.0.1:6379/0 uv run pytest` from `services/api` passed 169 tests, with 6 warnings and no failures. That suite does not include the MCP server tests or the agent tests under `tests/pipelines`.

## MCP Playground

Not run from this workspace. There is no Codespaces forwarded URL on record.

When a Codespace is available:

1. Set `MCP_HOST=0.0.0.0` and the issuer, audience, resource, scopes, and incidents URL.
2. Run `uv run company-tools`.
3. Forward the MCP port with public visibility.
4. In MCP Playground, use `https://<codespace>-<port>.app.github.dev/mcp`. Do not use localhost.
5. Present a bearer token whose `aud` is `MCP_AUTH_AUDIENCE` and whose scope includes the tool you call.
6. List tools, then call `get_status`, `create`, `update`, `product` or `stock`, and an inventory `update`.

`create`, `update`, and inventory reads return the errors in the table above. They do not store a ticket or a stock row.

## Known limitations

- The incidents API registers GET only. Create and update are rejected before any HTTP write. Lifecycle transitions stay with that API, which does not expose a status route.
- This repository has no inventory HTTP API. Product and stock lookups return `VALIDATION_ERROR`. Writes return `INVENTORY_WRITE_FORBIDDEN`.
- No OIDC issuer is configured in the repo. Startup exits 2 until `MCP_AUTH_ISSUER` and the other required settings are present and the issuer is reachable.
- MCP Playground evidence is not collected. Localhost is not a substitute.
- Acceptance status is in `docs/mcp/acceptance-readiness.md`. It remains not ready. Live OIDC steps are in `docs/mcp/oidc-validation.md`. Playground steps are in `docs/mcp/playground-validation.md`. Neither has been executed. Owner questions are in `docs/mcp/incident-lifecycle-decision.md` and `docs/mcp/inventory-read-decision.md`. No write route or inventory read was added.
- On 20 November 2026, `REDIS_URL=redis://127.0.0.1:6379/0 uv run pytest` from `services/api` passed 169 tests, with 6 warnings and no skips. The company-tools suite passed 19. The agent, routing, and RAG command passed 40, with no skips. Those runs do not prove live OIDC or Playground.
