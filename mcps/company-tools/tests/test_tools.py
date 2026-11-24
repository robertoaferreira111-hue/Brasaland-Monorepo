"""Incident and inventory tool behavior against the live service contracts."""

from __future__ import annotations

import asyncio

import httpx

from company_tools.auth import build_mcp_auth
from company_tools.config import load_settings
from company_tools.errors import INVENTORY_WRITE_FORBIDDEN, INVENTORY_WRITE_MESSAGE
from company_tools.server import create_mcp
from company_tools.tools import register_tools
from company_tools.tools.incidents import CREATE_MESSAGE, TOOL_NAME as INCIDENTS_TOOL, UPDATE_MESSAGE
from company_tools.tools.incidents import execute_incident_tool
from company_tools.tools.inventory import NO_ROUTE_MESSAGE, execute_inventory_tool
from tests.test_foundation import VALID_ENV, _auth_server

ENV = {
    "INCIDENTS_API_BASE_URL": "http://incidents.test",
    "INCIDENTS_API_TIMEOUT_SECONDS": "5",
    "INCIDENTS_API_TOKEN": "staff-token",
    "MCP_AUTH_ISSUER": "https://issuer.test",
    "MCP_AUTH_AUDIENCE": "https://mcp.test/mcp",
    "MCP_AUTH_RESOURCE": "https://mcp.test/mcp",
    "MCP_AUTH_SCOPES": "incidents.read,inventory.read",
    "MCP_AUTH_INCIDENTS_SCOPE": "incidents.read",
    "MCP_AUTH_INVENTORY_SCOPE": "inventory.read",
}

RECORD = {
    "incident_id": "BRS-000001",
    "date": "2024-01-14",
    "location_id": "COL-07",
    "category": "FOOD_QUALITY",
    "description": "Porción servida menor a la estándar del menú",
    "status": "CLOSED",
    "customer_id": "CLI-471507",
    "satisfaction_score": 5,
    "reporter_id": "MGR-01",
}


def test_discovery_describes_both_tools() -> None:
    settings = load_settings(VALID_ENV)
    mcp = create_mcp()
    register_tools(mcp, settings, build_mcp_auth(settings, _auth_server()))
    tools = {
        tool.name: tool
        for tool in asyncio.run(mcp.list_tools(run_middleware=False))
    }
    incident = tools["manage_incident_ticket"]
    inventory = tools["query_inventory"]
    assert "GET /api/incidents/{ticket_id}" in incident.description
    assert "GET only" in incident.description
    assert set(incident.parameters["properties"]) >= {
        "action",
        "ticket_id",
        "status",
        "category",
    }
    assert "INVENTORY_WRITE_FORBIDDEN" in inventory.description
    assert set(inventory.parameters["properties"]) >= {
        "action",
        "product_id",
        "quantity",
        "stock",
    }


def test_status_lookup_returns_the_incident_record() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=RECORD)

    result = execute_incident_tool(
        load_settings(ENV),
        action="get_status",
        ticket_id="BRS-000001",
        transport=httpx.MockTransport(handler),
        scopes=("incidents.read",),
    )
    assert result == {"tool": INCIDENTS_TOOL, "incident": RECORD}
    assert seen[0].method == "GET"
    assert seen[0].url.path == "/api/incidents/BRS-000001"
    assert seen[0].headers["authorization"] == "Bearer staff-token"


def test_list_sends_supported_filters() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[RECORD])

    result = execute_incident_tool(
        load_settings(ENV),
        action="list",
        status="OPEN",
        category="STAFF",
        transport=httpx.MockTransport(handler),
        scopes=("incidents.read",),
    )
    assert result == {"tool": INCIDENTS_TOOL, "incidents": [RECORD]}
    assert seen[0].method == "GET"
    assert seen[0].url.path == "/api/incidents"
    assert seen[0].url.params["status"] == "OPEN"
    assert seen[0].url.params["category"] == "STAFF"


def test_create_and_update_are_not_sent() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("a write must not call the incidents API")

    created = execute_incident_tool(
        load_settings(ENV),
        action="create",
        ticket_id="BRS-000001",
        transport=httpx.MockTransport(handler),
        scopes=("incidents.read",),
    )
    updated = execute_incident_tool(
        load_settings(ENV),
        action="update",
        ticket_id="BRS-000001",
        status="CLOSED",
        transport=httpx.MockTransport(handler),
        scopes=("incidents.read",),
    )
    assert created == {
        "error_code": "VALIDATION_ERROR",
        "message": CREATE_MESSAGE,
        "tool": INCIDENTS_TOOL,
    }
    assert updated == {
        "error_code": "VALIDATION_ERROR",
        "message": UPDATE_MESSAGE,
        "tool": INCIDENTS_TOOL,
    }


def test_invalid_ticket_input_is_rejected_before_http() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError("invalid input must not call the incidents API")

    transport = httpx.MockTransport(handler)
    settings = load_settings(ENV)
    missing = execute_incident_tool(
        settings,
        action="get_status",
        transport=transport,
        scopes=("incidents.read",),
    )
    malformed = execute_incident_tool(
        settings,
        action="get_status",
        ticket_id="482",
        transport=transport,
        scopes=("incidents.read",),
    )
    bad_status = execute_incident_tool(
        settings,
        action="update",
        ticket_id="BRS-000001",
        status="pending",
        transport=transport,
        scopes=("incidents.read",),
    )
    bad_filter = execute_incident_tool(
        settings,
        action="list",
        status="pending",
        transport=transport,
        scopes=("incidents.read",),
    )
    assert missing["message"] == "ticket_id is required."
    assert malformed["message"] == "ticket_id must match BRS-######."
    assert bad_status["message"] == "status must be OPEN, CLOSED, or DISCARDED."
    assert bad_filter["error_code"] == "VALIDATION_ERROR"
    assert all(item["tool"] == INCIDENTS_TOOL for item in (missing, malformed, bad_status, bad_filter))


def test_upstream_status_timeout_and_http_errors() -> None:
    settings = load_settings(ENV)

    def missing(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Incident not found"})

    def unavailable(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "Storage unavailable"})

    def rejected(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Not authenticated"})

    def timed_out(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    def down(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    not_found = execute_incident_tool(
        settings,
        action="get_status",
        ticket_id="BRS-999999",
        transport=httpx.MockTransport(missing),
        scopes=("incidents.read",),
    )
    storage = execute_incident_tool(
        settings,
        action="list",
        transport=httpx.MockTransport(unavailable),
        scopes=("incidents.read",),
    )
    credential = execute_incident_tool(
        settings,
        action="get_status",
        ticket_id="BRS-000001",
        transport=httpx.MockTransport(rejected),
        scopes=("incidents.read",),
    )
    timeout = execute_incident_tool(
        settings,
        action="get_status",
        ticket_id="BRS-000001",
        transport=httpx.MockTransport(timed_out),
        scopes=("incidents.read",),
    )
    failed = execute_incident_tool(
        settings,
        action="get_status",
        ticket_id="BRS-000001",
        transport=httpx.MockTransport(down),
        scopes=("incidents.read",),
    )
    assert not_found["message"] == "Incident not found"
    assert storage["message"] == "Storage unavailable"
    assert credential["message"] == "The incidents API rejected the service credential."
    assert "staff-token" not in credential["message"]
    assert timeout["message"] == "The incidents API did not respond before the timeout."
    assert failed["message"] == "The incidents API request failed."
    assert all(
        item["error_code"] == "UPSTREAM_ERROR"
        for item in (not_found, storage, credential, timeout, failed)
    )


def test_inventory_write_is_rejected_before_a_read() -> None:
    by_action = execute_inventory_tool(
        action="update",
        product_id="ITEM-PICANHA-250",
        scopes=(),
        required_scope="inventory.read",
    )
    by_quantity = execute_inventory_tool(
        action="product",
        product_id="ITEM-PICANHA-250",
        quantity=4,
        scopes=("inventory.read",),
        required_scope="inventory.read",
    )
    by_stock = execute_inventory_tool(
        action="stock",
        product_id="ITEM-PICANHA-250",
        stock=0,
        scopes=("inventory.read",),
        required_scope="inventory.read",
    )
    expected = {
        "error_code": INVENTORY_WRITE_FORBIDDEN,
        "message": INVENTORY_WRITE_MESSAGE,
        "tool": "query_inventory",
    }
    assert by_action == expected
    assert by_quantity == expected
    assert by_stock == expected


def test_inventory_reads_report_the_missing_route() -> None:
    product = execute_inventory_tool(
        action="product",
        product_id="ITEM-PICANHA-250",
        scopes=("inventory.read",),
        required_scope="inventory.read",
    )
    stock = execute_inventory_tool(
        action="stock",
        product_id="ITEM-PICANHA-250",
        scopes=("inventory.read",),
        required_scope="inventory.read",
    )
    assert product["error_code"] == "VALIDATION_ERROR"
    assert product["message"] == NO_ROUTE_MESSAGE
    assert stock["message"] == NO_ROUTE_MESSAGE
    assert product["tool"] == "query_inventory"


def test_inventory_invalid_filter_is_validation() -> None:
    unknown = execute_inventory_tool(
        action="category",
        product_id="ITEM-PICANHA-250",
        scopes=("inventory.read",),
        required_scope="inventory.read",
    )
    missing = execute_inventory_tool(
        action="stock",
        product_id="  ",
        scopes=("inventory.read",),
        required_scope="inventory.read",
    )
    assert unknown["error_code"] == "VALIDATION_ERROR"
    assert unknown["message"] == "action must be product or stock."
    assert missing["message"] == "product_id is required."
    assert unknown["error_code"] != INVENTORY_WRITE_FORBIDDEN
