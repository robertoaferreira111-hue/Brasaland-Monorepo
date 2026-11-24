# Incident lifecycle — owner decision request

No create or status-update route is added by this document. The reference solution's POST and status examples are not a contract. `company-BRIEFING.md` and `CONTEXT.md` do not define one.

## What the repository already does

- `services/api/app/routers/incidents.py` registers `GET /api/incidents` and `GET /api/incidents/{incident_id}` only.
- `tests/test_incidents_api.py` `test_openapi_lists_read_routes_only` asserts those OpenAPI methods are GET, and that `POST /api/incidents` returns 405.
- Stored records use `IncidentRecord`: `incident_id` (`BRS-######`), `date`, `location_id`, `category`, `description`, `status`, `customer_id`, `satisfaction_score`, `reporter_id`. Extra fields are rejected by that model. `incident_id`, `date`, `status`, and `reporter_id` are required on a stored record. `location_id`, `category`, `description`, `customer_id`, and `satisfaction_score` may be absent. `satisfaction_score`, when present, is an integer from 1 to 5.
- List filters already accepted on GET are status `OPEN`, `CLOSED`, or `DISCARDED`, and category `CUSTOMER_COMPLAINT`, `EQUIPMENT`, `SUPPLY`, `FOOD_QUALITY`, or `STAFF`.
- The incidents API authenticates with the existing staff bearer. That credential is `INCIDENTS_API_TOKEN` on the MCP server. It is not the MCP access token.
- CSV seeding inserts missing ids from `data/raw/incidents-brasaland.csv`. It is not a client create API.
- MCP action `create` returns `VALIDATION_ERROR` with `The incidents API exposes read routes only. Create was not sent.` Action `update` returns `VALIDATION_ERROR` with `The incidents API has no status-update route. The requested transition was not sent.` Neither call leaves the MCP process. The incidents scope is checked first: a token without `incidents.read` receives `INSUFFICIENT_SCOPE` instead.

## Decisions required before any write route

Answer these in writing. Do not treat an example payload as the answer.

1. Which stored fields may a client send on create, and which of those are required?
2. Who assigns `incident_id`: the client or the server?
3. Who sets `date` and `reporter_id`?
4. Which transitions among `OPEN`, `CLOSED`, and `DISCARDED` are legal, and from which starting status?
5. What should the API return for a missing field, an unknown status, and an illegal transition? Name the HTTP status. Do not reuse the MCP `VALIDATION_ERROR` body as that HTTP contract unless you decide to.
6. Does a write use the same staff bearer as GET?
7. May `test_openapi_lists_read_routes_only` change so POST or a status route is no longer a 405?

Until those answers exist, the MCP tool must keep rejecting `create` and `update` without sending a write.
