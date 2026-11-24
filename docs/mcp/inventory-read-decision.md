# Inventory reads — owner decision request

No inventory endpoint is added by this document. Telemetry events are not product or stock records.

## What the repository already does

- `docs/telemetry/README.md` states that the inventory application named in the briefing is not in this repository.
- `company-BRIEFING.md` does not define a product or stock API.
- No router in this repository serves product or stock reads.
- `data/dev/inventory_seed.py` and `data/dev/seed_inventory_events.py` insert synthetic telemetry events. They are not a catalog.
- `query_inventory` accepts read actions `product` and `stock`. After a `product_id` is present, the tool returns `VALIDATION_ERROR` with `This repository has no inventory HTTP route.` It does not call `INVENTORY_API_BASE_URL`.
- Actions `update`, `create`, `delete`, `write`, `set`, and `adjust`, and any call that sets `quantity` or `stock`, return `INVENTORY_WRITE_FORBIDDEN` with `Inventory tool is read-only. Write operations are not permitted on this MCP server.` That check runs before the inventory scope check and must remain.

## Decisions required before a read can succeed

1. Which service owns product and stock data?
2. Where does that service run: a repository path, or an external base URL?
3. What are the approved read endpoints for a product lookup and a stock lookup?
4. What query parameters and response fields are approved? Name required and optional fields.
5. What credential calls that service, and which MCP scope remains `inventory.read`?
6. What HTTP statuses and bodies should the MCP tool map to `VALIDATION_ERROR` and `UPSTREAM_ERROR`?

Until those answers exist, `product` and `stock` stay on the no-route error, and writes stay on `INVENTORY_WRITE_FORBIDDEN`.
