"""FastMCP application and Streamable HTTP entrypoint."""

from __future__ import annotations

import logging
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastmcp import FastMCP
from mcpauth.config import AuthServerConfig
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from company_tools.auth import AuthErrorCodeMiddleware, bearer_middleware, build_mcp_auth, fetch_auth_server
from company_tools.config import Settings, load_settings
from company_tools.errors import ConfigurationError
from company_tools.logging import configure_logging
from company_tools.tools import register_tools

SERVER_NAME = "Brasaland company tools"
logger = logging.getLogger("company_tools")


def create_mcp() -> FastMCP:
    """FastMCP with built-in OAuth left unset. mcpauth is attached in `create_app`."""
    return FastMCP(
        name=SERVER_NAME,
        instructions=(
            "Company tools for incident reads and read-only inventory. "
            "Incident create and update are rejected because the incidents API is GET only. "
            "Inventory writes are rejected. Discovery and calls require an OAuth bearer token."
        ),
        auth=None,
    )


def create_app(settings: Settings, auth_server: AuthServerConfig) -> Starlette:
    """Streamable HTTP app. `/health` and protected-resource metadata are public."""
    configure_logging()
    mcp = create_mcp()
    mcp_auth = build_mcp_auth(settings, auth_server)
    register_tools(mcp, settings, mcp_auth)
    mcp_app = mcp.http_app(
        path="/mcp",
        transport="streamable-http",
        stateless_http=True,
        host_origin_protection=False,
    )
    bearer = Middleware(
        bearer_middleware(mcp_auth, settings),
    )
    coded = Middleware(AuthErrorCodeMiddleware)

    def health(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "transport": settings.transport,
                "auth": "mcpauth",
                "resource": settings.mcp_auth_resource,
            }
        )

    return Starlette(
        routes=[
            Route("/health", endpoint=health, methods=["GET"]),
            *mcp_auth.resource_metadata_router().routes,
            Mount("/", app=mcp_app, middleware=[coded, bearer]),
        ],
        lifespan=mcp_app.lifespan,
    )


def main() -> None:
    configure_logging()
    _load_local_env()
    try:
        settings = load_settings()
        auth_server = fetch_auth_server(settings)
    except ConfigurationError as exc:
        logger.error("configuration failed: %s", exc)
        raise SystemExit(2) from exc
    except Exception as exc:
        logger.error("authorization server metadata fetch failed: %s", type(exc).__name__)
        raise SystemExit(2) from exc
    uvicorn.run(
        create_app(settings, auth_server),
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


def _load_local_env() -> None:
    path = Path(__file__).resolve().parents[1] / ".env"
    if path.is_file():
        load_dotenv(path, override=False)


if __name__ == "__main__":
    main()
