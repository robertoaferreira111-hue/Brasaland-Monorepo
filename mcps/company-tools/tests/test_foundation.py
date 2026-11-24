"""Foundation tests for the company-tools MCP server."""

from __future__ import annotations

import asyncio
import json

import pytest
from mcpauth.config import (
    AuthServerConfig,
    AuthServerType,
    AuthorizationServerMetadata,
)
from starlette.testclient import TestClient

from company_tools.config import load_settings
from company_tools.errors import ConfigurationError
from company_tools.logging import INVOCATION_LOGGER, configure_logging, log_invocation
from company_tools.server import SERVER_NAME, create_app, create_mcp
from company_tools.tools import register_tools
from company_tools.auth import build_mcp_auth

VALID_ENV = {
    "INCIDENTS_API_BASE_URL": "http://127.0.0.1:8000",
    "INCIDENTS_API_TIMEOUT_SECONDS": "5",
    "INCIDENTS_API_TOKEN": "staff-token",
    "MCP_AUTH_ISSUER": "https://issuer.test",
    "MCP_AUTH_AUDIENCE": "https://mcp.test/mcp",
    "MCP_AUTH_RESOURCE": "https://mcp.test/mcp",
    "MCP_AUTH_SCOPES": "incidents.read,inventory.read",
    "MCP_AUTH_INCIDENTS_SCOPE": "incidents.read",
    "MCP_AUTH_INVENTORY_SCOPE": "inventory.read",
}


def _auth_server() -> AuthServerConfig:
    return AuthServerConfig(
        type=AuthServerType.OIDC,
        metadata=AuthorizationServerMetadata(
            issuer="https://issuer.test",
            authorization_endpoint="https://issuer.test/authorize",
            token_endpoint="https://issuer.test/token",
            jwks_uri="https://issuer.test/jwks",
            response_types_supported=["code"],
            grant_types_supported=["authorization_code"],
            code_challenge_methods_supported=["S256"],
        ),
    )


def test_server_initializes() -> None:
    mcp = create_mcp()
    assert mcp.name == SERVER_NAME
    assert mcp.auth is None


def test_configuration_validation() -> None:
    settings = load_settings(VALID_ENV)
    assert settings.transport == "streamable-http"
    assert settings.port == 8080
    assert settings.incidents_timeout_seconds == 5.0
    assert settings.mcp_auth_scopes == ("incidents.read", "inventory.read")
    assert settings.incidents_scope == "incidents.read"
    assert settings.inventory_scope == "inventory.read"
    assert settings.inventory_api_base_url is None

    with pytest.raises(ConfigurationError) as invalid_timeout:
        load_settings({**VALID_ENV, "INCIDENTS_API_TIMEOUT_SECONDS": "0"})
    assert "INCIDENTS_API_TIMEOUT_SECONDS" in invalid_timeout.value.invalid

    with pytest.raises(ConfigurationError) as invalid_transport:
        load_settings({**VALID_ENV, "MCP_TRANSPORT": "stdio"})
    assert "MCP_TRANSPORT" in invalid_transport.value.invalid

    inventory = {
        **VALID_ENV,
        "INVENTORY_API_BASE_URL": "http://127.0.0.1:8000",
    }
    with pytest.raises(ConfigurationError) as missing_inventory_timeout:
        load_settings(inventory)
    assert "INVENTORY_API_TIMEOUT_SECONDS" in missing_inventory_timeout.value.invalid


def test_tool_registration() -> None:
    settings = load_settings(VALID_ENV)
    mcp = create_mcp()
    register_tools(mcp, settings, build_mcp_auth(settings, _auth_server()))
    tools = asyncio.run(mcp.list_tools(run_middleware=False))
    assert {tool.name for tool in tools} == {
        "manage_incident_ticket",
        "query_inventory",
    }


def test_transport_startup() -> None:
    app = create_app(load_settings(VALID_ENV), _auth_server())
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        body = health.json()
        assert body["status"] == "ok"
        assert body["transport"] == "streamable-http"
        assert body["auth"] == "mcpauth"
        metadata = client.get("/.well-known/oauth-protected-resource/mcp")
        assert metadata.status_code == 200
        assert metadata.json()["resource"] == "https://mcp.test/mcp"
        denied = client.get("/mcp")
        assert denied.status_code == 401
        assert denied.json()["error_code"] == "AUTH_MISSING_TOKEN"


def test_missing_configuration() -> None:
    for name in (
        "INCIDENTS_API_BASE_URL",
        "INCIDENTS_API_TIMEOUT_SECONDS",
        "INCIDENTS_API_TOKEN",
        "MCP_AUTH_ISSUER",
        "MCP_AUTH_AUDIENCE",
        "MCP_AUTH_RESOURCE",
        "MCP_AUTH_SCOPES",
        "MCP_AUTH_INCIDENTS_SCOPE",
        "MCP_AUTH_INVENTORY_SCOPE",
    ):
        env = {key: value for key, value in VALID_ENV.items() if key != name}
        with pytest.raises(ConfigurationError) as exc:
            load_settings(env)
        assert name in exc.value.missing


def test_logging_initialization(caplog: pytest.LogCaptureFixture) -> None:
    first = configure_logging()
    second = configure_logging()
    parent = first.parent
    assert parent is not None
    marked = [handler for handler in parent.handlers if getattr(handler, "_company_tools_handler", False)]
    assert len(marked) == 1
    assert first is second
    with caplog.at_level("INFO", logger=INVOCATION_LOGGER):
        log_invocation(
            client_id="agent-support",
            tool="manage_incident_ticket",
            input_summary={"action": "get_status", "ticket_id": "BRS-000001"},
            result="success",
            duration_ms=12,
        )
    payload = json.loads(caplog.records[-1].getMessage())
    assert payload["client_id"] == "agent-support"
    assert payload["tool"] == "manage_incident_ticket"
    assert payload["input_summary"] == {"action": "get_status", "ticket_id": "BRS-000001"}
    assert payload["result"] == "success"
    assert payload["duration_ms"] == 12
    assert "timestamp" in payload
    assert "staff-token" not in caplog.records[-1].getMessage()
