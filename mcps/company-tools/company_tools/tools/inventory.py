"""Inventory tool. Writes are rejected. No inventory HTTP route exists to call."""

from __future__ import annotations

import time
from typing import Annotated, Any

from fastmcp import FastMCP
from mcpauth import MCPAuth
from pydantic import Field

from company_tools.auth import scope_rejection
from company_tools.config import Settings
from company_tools.errors import (
    INVENTORY_WRITE_FORBIDDEN,
    INVENTORY_WRITE_MESSAGE,
    VALIDATION_ERROR,
    tool_error,
)
from company_tools.logging import log_invocation

TOOL_NAME = "query_inventory"
_WRITE_ACTIONS = {"update", "create", "delete", "write", "set", "adjust"}
_READ_ACTIONS = {"product", "stock"}
NO_ROUTE_MESSAGE = "This repository has no inventory HTTP route."


def register(mcp: FastMCP, settings: Settings, mcp_auth: MCPAuth) -> None:

    @mcp.tool(
        name=TOOL_NAME,
        description=(
            "Read-only inventory lookup. product looks up a product and stock looks up "
            "its stock. This repository has no inventory HTTP API, so those reads cannot "
            "be served from a live route. action update, or a quantity or stock input, "
            "is rejected with INVENTORY_WRITE_FORBIDDEN."
        ),
    )
    def query_inventory(
        action: Annotated[
            str | None,
            Field(
                description=(
                    "product or stock. update, create, delete, write, set, and adjust are rejected."
                )
            ),
        ] = None,
        product_id: Annotated[
            str | None,
            Field(description="Product identifier for a product or stock lookup."),
        ] = None,
        quantity: Annotated[
            int | None,
            Field(description="Write field. Any value is rejected. Inventory is read-only."),
        ] = None,
        stock: Annotated[
            int | None,
            Field(description="Write field. Any value is rejected. Inventory is read-only."),
        ] = None,
    ) -> dict[str, Any]:
        info = mcp_auth.auth_info
        scopes = tuple(info.scopes) if info is not None else ()
        client_id = info.client_id if info is not None and info.client_id else "unknown"
        return execute_inventory_tool(
            action=action,
            product_id=product_id,
            quantity=quantity,
            stock=stock,
            client_id=client_id,
            scopes=scopes,
            required_scope=settings.inventory_scope,
        )


def execute_inventory_tool(
    *,
    action: str | None = None,
    product_id: str | None = None,
    quantity: int | None = None,
    stock: int | None = None,
    client_id: str = "unknown",
    scopes: tuple[str, ...] = (),
    required_scope: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    outcome = _outcome(
        action=action,
        product_id=product_id,
        quantity=quantity,
        stock=stock,
        scopes=scopes,
        required_scope=required_scope,
    )
    log_invocation(
        client_id=client_id,
        tool=TOOL_NAME,
        input_summary={
            "action": action,
            "product_id": product_id,
            "quantity": quantity,
            "stock": stock,
        },
        result="failure" if "error_code" in outcome else "success",
        error_code=outcome.get("error_code"),
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
    return outcome


def _outcome(
    *,
    action: str | None,
    product_id: str | None,
    quantity: int | None,
    stock: int | None,
    scopes: tuple[str, ...],
    required_scope: str,
) -> dict[str, Any]:
    normalized = action.strip().lower() if isinstance(action, str) else None
    if normalized in _WRITE_ACTIONS or quantity is not None or stock is not None:
        return tool_error(INVENTORY_WRITE_FORBIDDEN, INVENTORY_WRITE_MESSAGE, TOOL_NAME)
    denied = scope_rejection(scopes, required_scope, TOOL_NAME)
    if denied is not None:
        return denied
    if normalized not in _READ_ACTIONS:
        return tool_error(VALIDATION_ERROR, "action must be product or stock.", TOOL_NAME)
    if product_id is None or not product_id.strip():
        return tool_error(VALIDATION_ERROR, "product_id is required.", TOOL_NAME)
    return tool_error(VALIDATION_ERROR, NO_ROUTE_MESSAGE, TOOL_NAME)
