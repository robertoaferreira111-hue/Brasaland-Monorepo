# Live OIDC validation procedure

Status: **pending**. This procedure is not evidence that a live issuer was used. Local JWKS tests in `mcps/company-tools/tests/test_auth.py` stay separate. Do not paste tokens, client secrets, or `INCIDENTS_API_TOKEN` into this file, logs, or screenshots.

The server reads `mcps/company-tools/.env` and does not override variables already set in the process. Root `.env/local` is the RAG file. It does not start this server.

## 1. Environment

Create `mcps/company-tools/.env`. Do not commit it.

| Variable | Required value |
| --- | --- |
| `MCP_TRANSPORT` | `streamable-http` |
| `MCP_HOST` | `0.0.0.0` when a Codespace must reach the process. `127.0.0.1` is the local default. |
| `MCP_PORT` | `8080` |
| `INCIDENTS_API_BASE_URL` | Base URL of the running incidents API. No path suffix. |
| `INCIDENTS_API_TIMEOUT_SECONDS` | A number greater than 0. |
| `INCIDENTS_API_TOKEN` | Staff bearer for that API. Not the MCP access token. |
| `MCP_AUTH_ISSUER` | HTTPS origin of a compliant OIDC issuer. No trailing discovery path. |
| `MCP_AUTH_AUDIENCE` | Value the access token must carry in `aud`. |
| `MCP_AUTH_RESOURCE` | Protected-resource identifier. Use the public MCP URL, including `/mcp`, once Codespaces assigns it. |
| `MCP_AUTH_SCOPES` | `incidents.read,inventory.read` |
| `MCP_AUTH_INCIDENTS_SCOPE` | `incidents.read` |
| `MCP_AUTH_INVENTORY_SCOPE` | `inventory.read` |

Both tool scopes must be members of `MCP_AUTH_SCOPES` and must differ. `INVENTORY_API_BASE_URL` stays empty until an inventory read contract exists.

## 2. Issuer discovery and JWKS

Before startup, fetch `{MCP_AUTH_ISSUER}/.well-known/openid-configuration`.

Confirm the JSON includes `jwks_uri`. Fetch that URL and confirm it returns signing keys. Do not copy the keys into the report. Record only the HTTP status, the issuer host, and that `jwks_uri` was present.

`fetch_auth_server` calls `fetch_server_config` with OIDC and exits if `jwks_uri` is missing.

## 3. Startup

From `mcps/company-tools`:

```bash
uv run company-tools
```

Missing settings, or a failed issuer fetch, exit 2. A live run is shown by the process staying up and `GET /health` returning `status` `ok`, `auth` `mcpauth`, and `resource` equal to `MCP_AUTH_RESOURCE`. `/health` is public and must not echo the staff token.

## 4. Protected-resource metadata

Metadata is public. When `MCP_AUTH_RESOURCE` ends in `/mcp`, request:

`GET /.well-known/oauth-protected-resource/mcp`

Confirm the document identifies that resource, names the authorization server, and lists `incidents.read` and `inventory.read`. `resource_name` in this server is `Brasaland company tools`. Save the response with secrets removed.

## 5. Token claims

Issue tokens from the configured issuer. Do not print them. A token the middleware can accept has:

- `iss` equal to `MCP_AUTH_ISSUER`
- `aud` equal to `MCP_AUTH_AUDIENCE`
- a future `exp`
- a `scope` string

Discovery does not require a tool scope. A valid token with either scope can list tools. Invocation checks the tool scope after the JWT is accepted.

## 6. Scenarios

Use Streamable HTTP against the server's `/mcp` path. Record the HTTP status and the `error_code`. Redact the bearer value.

| Scenario | Expected result |
| --- | --- |
| No `Authorization` header, `tools/list` and `tools/call` | HTTP 401, `AUTH_MISSING_TOKEN`, message `An OAuth access token is required.` |
| Token `not-a-jwt`, or any token the issuer JWKS cannot verify | HTTP 401, `AUTH_INVALID_TOKEN`, message `The OAuth access token is invalid or expired.` |
| Token with `exp` in the past, beyond the validator leeway | HTTP 401, `AUTH_INVALID_TOKEN`, same message. Expiry is not a separate code. |
| Valid token, `tools/list` | HTTP 200. Both `manage_incident_ticket` and `query_inventory` appear, with their input schemas. |
| Valid token whose `scope` includes `incidents.read`, `manage_incident_ticket` action `get_status` or `list` | HTTP 200. A successful call returns incident data from the live GET API. This is not a create or a status update. |
| Valid token whose `scope` is only `inventory.read`, `manage_incident_ticket` action `list` | HTTP 200 with tool body `INSUFFICIENT_SCOPE` and message `The access token does not include the scope required for this operation.` This is an authorization result, not HTTP 401. |
| Valid token whose `scope` includes `incidents.read`, action `create` | HTTP 200 with tool body `VALIDATION_ERROR`: `The incidents API exposes read routes only. Create was not sent.` Scope is checked before that rejection. A token without `incidents.read` receives `INSUFFICIENT_SCOPE` instead. |
| `query_inventory` action `update`, or any call that sets `quantity` or `stock` | Tool body `INVENTORY_WRITE_FORBIDDEN`. The write check runs before the inventory scope check. |

## 7. Evidence to keep

Store redacted output under `docs/mcp/evidence/`. Include:

- discovery HTTP status and the presence of `jwks_uri`
- JWKS HTTP status, without the key material
- startup remaining up, or the exit code
- `/health` body
- protected-resource metadata
- one valid `tools/list`
- one authorized incident `get_status` or `list`
- missing, invalid, expired, and insufficient-scope results

Live issuer validation stays pending until those files exist. The local JWKS suite does not fill this list.
