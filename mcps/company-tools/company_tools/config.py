"""Environment configuration for the MCP server.

Only the process environment is read. A local `.env` next to this project is
loaded by `server.main` and does not override variables that are already set.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from company_tools.errors import ConfigurationError

TRANSPORT = "streamable-http"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

_REQUIRED = (
    "INCIDENTS_API_BASE_URL",
    "INCIDENTS_API_TIMEOUT_SECONDS",
    "INCIDENTS_API_TOKEN",
    "MCP_AUTH_ISSUER",
    "MCP_AUTH_AUDIENCE",
    "MCP_AUTH_RESOURCE",
    "MCP_AUTH_SCOPES",
    "MCP_AUTH_INCIDENTS_SCOPE",
    "MCP_AUTH_INVENTORY_SCOPE",
)


@dataclass(frozen=True)
class Settings:
    transport: str
    host: str
    port: int
    incidents_api_base_url: str
    incidents_timeout_seconds: float
    incidents_api_token: str
    mcp_auth_issuer: str
    mcp_auth_audience: str
    mcp_auth_resource: str
    mcp_auth_scopes: tuple[str, ...]
    incidents_scope: str
    inventory_scope: str
    inventory_api_base_url: str | None
    inventory_timeout_seconds: float | None


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Build settings from `environ`, or from `os.environ` when it is omitted."""
    source = os.environ if environ is None else environ
    missing: list[str] = []
    invalid: list[str] = []
    values = {name: _text(source.get(name)) for name in _REQUIRED}
    for name, value in values.items():
        if value is None:
            missing.append(name)

    transport = _text(source.get("MCP_TRANSPORT")) or TRANSPORT
    if transport != TRANSPORT:
        invalid.append("MCP_TRANSPORT")

    host = _text(source.get("MCP_HOST")) or DEFAULT_HOST
    port = _port(source.get("MCP_PORT"), invalid)
    incidents_url = _http_url(values["INCIDENTS_API_BASE_URL"], "INCIDENTS_API_BASE_URL", invalid)
    incidents_timeout = _timeout(
        values["INCIDENTS_API_TIMEOUT_SECONDS"],
        "INCIDENTS_API_TIMEOUT_SECONDS",
        invalid,
    )
    issuer = _http_url(values["MCP_AUTH_ISSUER"], "MCP_AUTH_ISSUER", invalid)
    audience = values["MCP_AUTH_AUDIENCE"]
    resource = _http_url(values["MCP_AUTH_RESOURCE"], "MCP_AUTH_RESOURCE", invalid)
    scopes = _scopes(values["MCP_AUTH_SCOPES"], invalid)
    incidents_scope = values["MCP_AUTH_INCIDENTS_SCOPE"]
    inventory_scope = values["MCP_AUTH_INVENTORY_SCOPE"]
    if scopes and incidents_scope and incidents_scope not in scopes:
        invalid.append("MCP_AUTH_INCIDENTS_SCOPE")
    if scopes and inventory_scope and inventory_scope not in scopes:
        invalid.append("MCP_AUTH_INVENTORY_SCOPE")
    if incidents_scope and inventory_scope and incidents_scope == inventory_scope:
        invalid.append("MCP_AUTH_INVENTORY_SCOPE")
    inventory_url, inventory_timeout = _inventory(source, invalid)

    if missing or invalid:
        raise ConfigurationError(missing=missing, invalid=invalid)

    assert (
        incidents_url
        and incidents_timeout
        and issuer
        and resource
        and scopes
        and incidents_scope
        and inventory_scope
    )
    return Settings(
        transport=transport,
        host=host,
        port=port,
        incidents_api_base_url=incidents_url,
        incidents_timeout_seconds=incidents_timeout,
        incidents_api_token=values["INCIDENTS_API_TOKEN"] or "",
        mcp_auth_issuer=issuer,
        mcp_auth_audience=audience or "",
        mcp_auth_resource=resource,
        mcp_auth_scopes=scopes,
        incidents_scope=incidents_scope,
        inventory_scope=inventory_scope,
        inventory_api_base_url=inventory_url,
        inventory_timeout_seconds=inventory_timeout,
    )


def _inventory(
    source: Mapping[str, str], invalid: list[str]
) -> tuple[str | None, float | None]:
    url_text = _text(source.get("INVENTORY_API_BASE_URL"))
    timeout_text = _text(source.get("INVENTORY_API_TIMEOUT_SECONDS"))
    if url_text is None:
        return None, None
    url = _http_url(url_text, "INVENTORY_API_BASE_URL", invalid)
    if timeout_text is None:
        invalid.append("INVENTORY_API_TIMEOUT_SECONDS")
        return url, None
    timeout = _timeout(timeout_text, "INVENTORY_API_TIMEOUT_SECONDS", invalid)
    return url, timeout


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _port(value: str | None, invalid: list[str]) -> int:
    text = _text(value)
    if text is None:
        return DEFAULT_PORT
    try:
        port = int(text)
    except ValueError:
        invalid.append("MCP_PORT")
        return DEFAULT_PORT
    if port < 1 or port > 65535:
        invalid.append("MCP_PORT")
        return DEFAULT_PORT
    return port


def _timeout(value: str | None, name: str, invalid: list[str]) -> float | None:
    if value is None:
        return None
    try:
        timeout = float(value)
    except ValueError:
        invalid.append(name)
        return None
    if timeout <= 0 or timeout != timeout or timeout == float("inf"):
        invalid.append(name)
        return None
    return timeout


def _http_url(value: str | None, name: str, invalid: list[str]) -> str | None:
    if value is None:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        invalid.append(name)
        return None
    return value.rstrip("/")


def _scopes(value: str | None, invalid: list[str]) -> tuple[str, ...] | None:
    if value is None:
        return None
    scopes = tuple(part.strip() for part in value.split(",") if part.strip())
    if not scopes:
        invalid.append("MCP_AUTH_SCOPES")
        return None
    return scopes
