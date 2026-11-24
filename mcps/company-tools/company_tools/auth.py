"""MCP Auth resource-server wiring.

FastMCP's own `auth=` argument stays unset. This module uses mcpauth 0.2
resource-server mode: OIDC metadata from `fetch_server_config`, protected
resource metadata, and `bearer_auth_middleware("jwt")` with the resource
identifier and audience. Each tool checks its own scope. One middleware
scope list would make every caller hold every tool permission.
"""

from __future__ import annotations

import json

from mcpauth import MCPAuth
from mcpauth.config import AuthServerConfig, AuthServerType
from mcpauth.types import ResourceServerConfig, ResourceServerMetadata
from mcpauth.utils import fetch_server_config
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from company_tools.config import Settings
from company_tools.errors import (
    AUTH_INVALID_TOKEN,
    AUTH_INVALID_TOKEN_MESSAGE,
    AUTH_MISSING_TOKEN,
    AUTH_MISSING_TOKEN_MESSAGE,
    INSUFFICIENT_SCOPE,
    INSUFFICIENT_SCOPE_MESSAGE,
    ConfigurationError,
    tool_error,
)

_MISSING_TOKEN_ERRORS = {
    "missing_auth_header",
    "invalid_auth_header_format",
    "missing_bearer_token",
}
_SCOPE_ERRORS = {"missing_required_scopes", "insufficient_scope"}


def fetch_auth_server(settings: Settings) -> AuthServerConfig:
    """Load OIDC metadata. This performs a network call and is not used by the unit tests."""
    config = fetch_server_config(settings.mcp_auth_issuer, AuthServerType.OIDC)
    _require_jwks(config)
    return config


def build_mcp_auth(settings: Settings, auth_server: AuthServerConfig) -> MCPAuth:
    _require_jwks(auth_server)
    return MCPAuth(
        protected_resources=ResourceServerConfig(
            metadata=ResourceServerMetadata(
                resource=settings.mcp_auth_resource,
                authorization_servers=[auth_server],
                scopes_supported=list(settings.mcp_auth_scopes),
                resource_name="Brasaland company tools",
            )
        )
    )


def bearer_middleware(mcp_auth: MCPAuth, settings: Settings) -> type[BaseHTTPMiddleware]:
    """JWT bearer check for the MCP mount. Tool scopes are enforced separately."""
    return mcp_auth.bearer_auth_middleware(
        "jwt",
        resource=settings.mcp_auth_resource,
        audience=settings.mcp_auth_audience,
    )


def scope_rejection(scopes: tuple[str, ...], required: str, tool: str) -> dict[str, str] | None:
    """Return an authorization error when `required` is not among `scopes`."""
    if required in scopes:
        return None
    return tool_error(INSUFFICIENT_SCOPE, INSUFFICIENT_SCOPE_MESSAGE, tool)


class AuthErrorCodeMiddleware(BaseHTTPMiddleware):
    """Replace mcpauth's OAuth error body with this server's error codes.

    HTTP 401 stays an authentication failure. HTTP 403 stays an authorization
    failure. The status code is not changed.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        if response.status_code not in {401, 403}:
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        payload = _json_object(body)
        status, content = translate_auth_error(response.status_code, payload)
        headers = {}
        authenticate = response.headers.get("www-authenticate")
        if authenticate:
            headers["WWW-Authenticate"] = authenticate
        return JSONResponse(status_code=status, content=content, headers=headers)


def translate_auth_error(status: int, payload: dict) -> tuple[int, dict[str, str]]:
    error = str(payload.get("error") or "")
    if status == 403 or error in _SCOPE_ERRORS:
        return 403, {
            "error_code": INSUFFICIENT_SCOPE,
            "message": INSUFFICIENT_SCOPE_MESSAGE,
        }
    if error in _MISSING_TOKEN_ERRORS:
        return 401, {
            "error_code": AUTH_MISSING_TOKEN,
            "message": AUTH_MISSING_TOKEN_MESSAGE,
        }
    return 401, {
        "error_code": AUTH_INVALID_TOKEN,
        "message": AUTH_INVALID_TOKEN_MESSAGE,
    }


def _require_jwks(auth_server: AuthServerConfig) -> None:
    if not auth_server.metadata.jwks_uri:
        raise ConfigurationError(invalid=["MCP_AUTH_ISSUER"])


def _json_object(body: bytes) -> dict:
    if not body:
        return {}
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}
