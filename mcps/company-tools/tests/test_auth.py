"""Authentication and authorization on discovery and invocation."""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from mcpauth.config import (
    AuthServerConfig,
    AuthServerType,
    AuthorizationServerMetadata,
)
from starlette.testclient import TestClient

from company_tools.config import load_settings
from company_tools.logging import INVOCATION_LOGGER, log_invocation
from company_tools.server import create_app

ENV = {
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
ISSUER = "https://issuer.test"
AUDIENCE = "https://mcp.test/mcp"


@pytest.fixture
def signing_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    public.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
    body = json.dumps({"keys": [public]}).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield {"key": key, "jwks": f"http://{host}:{port}/jwks"}
    finally:
        server.shutdown()


def _auth_server(jwks: str) -> AuthServerConfig:
    return AuthServerConfig(
        type=AuthServerType.OIDC,
        metadata=AuthorizationServerMetadata(
            issuer=ISSUER,
            authorization_endpoint=f"{ISSUER}/authorize",
            token_endpoint=f"{ISSUER}/token",
            jwks_uri=jwks,
            response_types_supported=["code"],
            grant_types_supported=["authorization_code"],
            code_challenge_methods_supported=["S256"],
        ),
    )


def _token(key, scope: str, *, expires_in: int = 600) -> str:
    now = int(time.time())
    encoded = jwt.encode(
        {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": "agent-user",
            "client_id": "agent-support",
            "scope": scope,
            "iat": now - 30,
            "exp": now + expires_in,
        },
        key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    if isinstance(encoded, bytes):
        return encoded.decode()
    return encoded


def _headers(token: str | None = None, *, method: str | None = None, name: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "mcp-protocol-version": "2026-07-28",
    }
    if method is not None:
        headers["mcp-method"] = method
    if name is not None:
        headers["mcp-name"] = name
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _post(client: TestClient, method: str, token: str | None = None, arguments: dict | None = None):
    params: dict = {
        "_meta": {
            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientCapabilities": {},
        }
    }
    name = None
    if method == "tools/call":
        name = "manage_incident_ticket"
        params["name"] = name
        params["arguments"] = arguments or {}
    return client.post(
        "/mcp",
        headers=_headers(token, method=method, name=name),
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )


def test_no_token_rejects_discovery_and_invocation(signing_key) -> None:
    app = create_app(load_settings(ENV), _auth_server(signing_key["jwks"]))
    with TestClient(app) as client:
        discovery = _post(client, "tools/list")
        invocation = _post(client, "tools/call", arguments={"action": "list"})
    assert discovery.status_code == 401
    assert discovery.json()["error_code"] == "AUTH_MISSING_TOKEN"
    assert discovery.json()["message"]
    assert invocation.status_code == 401
    assert invocation.json()["error_code"] == "AUTH_MISSING_TOKEN"
    assert "staff-token" not in discovery.text


def test_invalid_and_expired_tokens_are_rejected(signing_key) -> None:
    app = create_app(load_settings(ENV), _auth_server(signing_key["jwks"]))
    expired = _token(signing_key["key"], "incidents.read", expires_in=-180)
    with TestClient(app) as client:
        invalid = _post(client, "tools/list", token="not-a-jwt")
        stale = _post(client, "tools/call", token=expired, arguments={"action": "list"})
    assert invalid.status_code == 401
    assert invalid.json() == {
        "error_code": "AUTH_INVALID_TOKEN",
        "message": "The OAuth access token is invalid or expired.",
    }
    assert stale.status_code == 401
    assert stale.json()["error_code"] == "AUTH_INVALID_TOKEN"
    assert expired not in stale.text


def test_valid_token_is_accepted_and_missing_scope_is_authorization(
    signing_key, caplog: pytest.LogCaptureFixture
) -> None:
    app = create_app(load_settings(ENV), _auth_server(signing_key["jwks"]))
    allowed = _token(signing_key["key"], "incidents.read")
    inventory_only = _token(signing_key["key"], "inventory.read")
    with TestClient(app) as client:
        with caplog.at_level("INFO", logger=INVOCATION_LOGGER):
            listed = _post(client, "tools/list", token=allowed)
            accepted = _post(
                client,
                "tools/call",
                token=allowed,
                arguments={"action": "create"},
            )
            denied = _post(
                client,
                "tools/call",
                token=inventory_only,
                arguments={"action": "list"},
            )
    assert listed.status_code == 200
    assert "manage_incident_ticket" in listed.text
    assert "query_inventory" in listed.text
    assert accepted.status_code == 200
    assert "VALIDATION_ERROR" in accepted.text
    assert "AUTH_INVALID_TOKEN" not in accepted.text
    assert denied.status_code == 200
    assert "INSUFFICIENT_SCOPE" in denied.text
    assert "AUTH_MISSING_TOKEN" not in denied.text
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "staff-token" not in logged
    assert allowed not in logged
    assert inventory_only not in logged
    assert "VALIDATION_ERROR" in logged
    assert "INSUFFICIENT_SCOPE" in logged


def test_secret_redaction(caplog: pytest.LogCaptureFixture) -> None:
    from company_tools.logging import INVOCATION_LOGGER

    secret = "Bearer staff-token"
    description = "Customer Ana reported a cold steak."
    jwt_like = "aaaaaaaaaaa.bbbbbbbbbbb.ccccccccccc"
    with caplog.at_level("INFO", logger=INVOCATION_LOGGER):
        log_invocation(
            client_id="agent-support",
            tool="manage_incident_ticket",
            input_summary={
                "action": "get_status",
                "ticket_id": "BRS-000001",
                "authorization": secret,
                "description": description,
                "note": jwt_like,
            },
            result="failure",
            error_code="VALIDATION_ERROR",
            duration_ms=4,
        )
    line = caplog.records[-1].getMessage()
    payload = json.loads(line)
    assert payload["input_summary"]["ticket_id"] == "BRS-000001"
    assert payload["input_summary"]["authorization"] == "[redacted]"
    assert payload["input_summary"]["description"] == "[redacted]"
    assert payload["input_summary"]["note"] == "[redacted]"
    assert payload["error_code"] == "VALIDATION_ERROR"
    assert payload["result"] == "failure"
    assert secret not in line
    assert description not in line
    assert jwt_like not in line
