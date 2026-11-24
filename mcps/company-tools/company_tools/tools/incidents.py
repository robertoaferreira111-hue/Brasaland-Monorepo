"""Incident tool. Calls the live incidents API. Does not apply status transitions."""

from __future__ import annotations

import re
import time
from typing import Annotated, Any
from urllib.parse import quote

import httpx
from fastmcp import FastMCP
from mcpauth import MCPAuth
from pydantic import Field

from company_tools.auth import scope_rejection
from company_tools.config import Settings
from company_tools.errors import UPSTREAM_ERROR, VALIDATION_ERROR, tool_error
from company_tools.logging import log_invocation

TOOL_NAME = "manage_incident_ticket"
_ACTIONS = {"list", "get_status", "create", "update"}
_STATUSES = ("OPEN", "CLOSED", "DISCARDED")
_CATEGORIES = ("CUSTOMER_COMPLAINT", "EQUIPMENT", "SUPPLY", "FOOD_QUALITY", "STAFF")
_TICKET_ID = re.compile(r"^BRS-\d{6}$")
_SAFE_DETAILS = {
    "Incident not found",
    "Storage unavailable",
    "Stored incident data is invalid",
}

CREATE_MESSAGE = "The incidents API exposes read routes only. Create was not sent."
UPDATE_MESSAGE = (
    "The incidents API has no status-update route. The requested transition was not sent."
)


def register(mcp: FastMCP, settings: Settings, mcp_auth: MCPAuth) -> None:
    @mcp.tool(
        name=TOOL_NAME,
        description=(
            "Look up one incident or list incidents from the company incidents API. "
            "get_status calls GET /api/incidents/{ticket_id}. "
            "list calls GET /api/incidents and may filter by status and category. "
            "create and update are accepted as actions and rejected: that API registers "
            "GET only, and this tool does not invent a write or a lifecycle transition."
        ),
    )
    def manage_incident_ticket(
        action: Annotated[
            str,
            Field(
                description=(
                    "list, get_status, create, or update. "
                    "create and update are rejected because the incidents API is read-only."
                )
            ),
        ],
        ticket_id: Annotated[
            str | None,
            Field(description="Incident id shaped BRS-######. Required for get_status and update."),
        ] = None,
        status: Annotated[
            str | None,
            Field(description="OPEN, CLOSED, or DISCARDED. List filter, or the target status for update."),
        ] = None,
        category: Annotated[
            str | None,
            Field(
                description=(
                    "List filter: CUSTOMER_COMPLAINT, EQUIPMENT, SUPPLY, FOOD_QUALITY, or STAFF."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        info = mcp_auth.auth_info
        scopes = tuple(info.scopes) if info is not None else ()
        client_id = info.client_id if info is not None and info.client_id else "unknown"
        return execute_incident_tool(
            settings,
            action=action,
            ticket_id=ticket_id,
            status=status,
            category=category,
            client_id=client_id,
            scopes=scopes,
        )


def execute_incident_tool(
    settings: Settings,
    *,
    action: str,
    ticket_id: str | None = None,
    status: str | None = None,
    category: str | None = None,
    client_id: str = "unknown",
    scopes: tuple[str, ...] = (),
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    denied = scope_rejection(scopes, settings.incidents_scope, TOOL_NAME)
    if denied is not None:
        outcome = denied
    else:
        try:
            outcome = _dispatch(
                settings,
                action=action,
                ticket_id=ticket_id,
                status=status,
                category=category,
                transport=transport,
            )
        except httpx.TimeoutException:
            outcome = tool_error(
                UPSTREAM_ERROR,
                "The incidents API did not respond before the timeout.",
                TOOL_NAME,
            )
        except httpx.HTTPError:
            outcome = tool_error(
                UPSTREAM_ERROR,
                "The incidents API request failed.",
                TOOL_NAME,
            )
    log_invocation(
        client_id=client_id,
        tool=TOOL_NAME,
        input_summary={
            "action": action,
            "ticket_id": ticket_id,
            "status": status,
            "category": category,
        },
        result="failure" if "error_code" in outcome else "success",
        error_code=outcome.get("error_code"),
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
    return outcome


def _dispatch(
    settings: Settings,
    *,
    action: str,
    ticket_id: str | None,
    status: str | None,
    category: str | None,
    transport: httpx.BaseTransport | None,
) -> dict[str, Any]:
    if action not in _ACTIONS:
        return tool_error(
            VALIDATION_ERROR,
            "action must be list, get_status, create, or update.",
            TOOL_NAME,
        )
    invalid = _invalid_input(action, ticket_id, status, category)
    if invalid is not None:
        return invalid
    if action == "create":
        return tool_error(VALIDATION_ERROR, CREATE_MESSAGE, TOOL_NAME)
    if action == "update":
        return tool_error(VALIDATION_ERROR, UPDATE_MESSAGE, TOOL_NAME)
    if action == "list":
        params = {
            key: value
            for key, value in (("status", status), ("category", category))
            if value
        }
        return _get(settings, "/api/incidents", params or None, transport, many=True)
    assert ticket_id is not None
    return _get(
        settings,
        f"/api/incidents/{quote(ticket_id, safe='')}",
        None,
        transport,
        many=False,
    )


def _invalid_input(
    action: str,
    ticket_id: str | None,
    status: str | None,
    category: str | None,
) -> dict[str, str] | None:
    if ticket_id is not None and _TICKET_ID.fullmatch(ticket_id) is None:
        return tool_error(VALIDATION_ERROR, "ticket_id must match BRS-######.", TOOL_NAME)
    if status is not None and status not in _STATUSES:
        return tool_error(
            VALIDATION_ERROR,
            "status must be OPEN, CLOSED, or DISCARDED.",
            TOOL_NAME,
        )
    if category is not None and category not in _CATEGORIES:
        return tool_error(
            VALIDATION_ERROR,
            "category must be CUSTOMER_COMPLAINT, EQUIPMENT, SUPPLY, FOOD_QUALITY, or STAFF.",
            TOOL_NAME,
        )
    if action in {"get_status", "update"} and not ticket_id:
        return tool_error(VALIDATION_ERROR, "ticket_id is required.", TOOL_NAME)
    if action == "update" and status is None:
        return tool_error(VALIDATION_ERROR, "status is required.", TOOL_NAME)
    return None


def _get(
    settings: Settings,
    path: str,
    params: dict[str, str] | None,
    transport: httpx.BaseTransport | None,
    *,
    many: bool,
) -> dict[str, Any]:
    url = f"{settings.incidents_api_base_url}{path}"
    headers = {"Authorization": f"Bearer {settings.incidents_api_token}"}
    timeout = httpx.Timeout(settings.incidents_timeout_seconds)
    with httpx.Client(timeout=timeout, transport=transport) as client:
        response = client.get(url, params=params, headers=headers)
    if response.status_code >= 400:
        return _http_error(response)
    try:
        body = response.json()
    except ValueError:
        return tool_error(
            UPSTREAM_ERROR,
            "The incidents API returned a non-JSON body.",
            TOOL_NAME,
        )
    if many:
        if not isinstance(body, list):
            return tool_error(
                UPSTREAM_ERROR,
                "The incidents API returned an unexpected body.",
                TOOL_NAME,
            )
        return {"tool": TOOL_NAME, "incidents": body}
    if not isinstance(body, dict):
        return tool_error(
            UPSTREAM_ERROR,
            "The incidents API returned an unexpected body.",
            TOOL_NAME,
        )
    return {"tool": TOOL_NAME, "incident": body}


def _http_error(response: httpx.Response) -> dict[str, str]:
    detail = _safe_detail(response)
    if response.status_code == 404:
        return tool_error(UPSTREAM_ERROR, detail or "Incident not found", TOOL_NAME)
    if response.status_code == 422:
        return tool_error(
            VALIDATION_ERROR,
            "The incidents API rejected the query.",
            TOOL_NAME,
        )
    if response.status_code in {401, 403}:
        return tool_error(
            UPSTREAM_ERROR,
            "The incidents API rejected the service credential.",
            TOOL_NAME,
        )
    if response.status_code >= 500:
        return tool_error(
            UPSTREAM_ERROR,
            detail or "The incidents API is unavailable.",
            TOOL_NAME,
        )
    return tool_error(
        UPSTREAM_ERROR,
        f"The incidents API returned {response.status_code}.",
        TOOL_NAME,
    )


def _safe_detail(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    detail = body.get("detail")
    if isinstance(detail, str) and detail in _SAFE_DETAILS:
        return detail
    return None
