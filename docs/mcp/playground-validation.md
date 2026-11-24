# MCP Playground validation procedure

Status: **pending**. No Playground session has been run. A localhost URL is not evidence.

## Access

The MCP server is in the local working tree. `feat/mcp-company-tools`, `main`, and `origin/main` point at the same commit, and that commit does not contain this server. A Codespace created from `origin/main` will not have `mcps/company-tools`.

Before opening a Codespace, the working tree has to be present there. Putting it on the remote requires an explicit Git write, which is not authorized in this phase. Do not treat a Codespace of `origin/main` as a test of this server.

`gh` on the machine used for Phase 5.2B was logged in and lacked the `codespace` scope. Refresh it in a terminal you control:

```bash
gh auth refresh -h github.com -s codespace
```

Approve the scope, then create a Codespace from the repository that contains this working tree.

## Server

In the Codespace, from `mcps/company-tools`, use the environment in `docs/mcp/oidc-validation.md`.

Set:

- `MCP_HOST=0.0.0.0`
- `MCP_PORT=8080`
- `MCP_AUTH_RESOURCE` to the public forwarded URL, including `/mcp`

Start:

```bash
uv run company-tools
```

In the Codespace ports panel, set port **8080** visibility to **public**.

The Playground URL is:

`https://<codespace>-8080.app.github.dev/mcp`

Copy it from the ports panel. Do not replace it with `http://127.0.0.1:8080/mcp` or `http://localhost:8080/mcp`.

## Playground

Open [MCP Playground](https://www.mcpplayground.tech/playground). Connect to the forwarded URL with a bearer token from the configured issuer. Do not paste the token into the repository.

Show these, in order:

1. Authenticated connection. The server accepts the token.
2. Tool discovery. `manage_incident_ticket` and `query_inventory` are both listed.
3. Both input schemas are visible.
4. `manage_incident_ticket` with action `get_status` and a `ticket_id` that `GET /api/incidents` already returns. The id shape is `BRS-######`.
5. `manage_incident_ticket` with action `list`.
6. `query_inventory` with action `update`. The result is `INVENTORY_WRITE_FORBIDDEN` and the message `Inventory tool is read-only. Write operations are not permitted on this MCP server.`

`create`, status `update`, and inventory `product` or `stock` are not successful operations. With a token that has the matching scope they return `VALIDATION_ERROR`. Record them only as the current rejection, not as a completed write or stock lookup.

## Evidence

Save screenshots under `docs/mcp/evidence/`. Each shot must show the public `*.app.github.dev` host and the `/mcp` path. Cover discovery, both schemas, one lookup, one list, and the inventory write rejection.

Do not store the access token, the staff token, or an `Authorization` header. This directory is empty of that evidence until those files are added. Playground validation is not complete while the directory has no such files.
