"""Incident operations through the company MCP server.

langchain-mcp-adapters opens one Streamable HTTP session, loads the server
tools, calls `manage_incident_ticket`, and closes the session. This module
does not read the incident database and does not call the incidents API.
The staff credential stays on the MCP server. `MCP_ACCESS_TOKEN` is sent only
as the bearer header for that session.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

NOT_RECORDED = "not recorded"
_TOOL_NAME = "manage_incident_ticket"
_SERVER_NAME = "company-tools"
_DEFAULT_TIMEOUT_SECONDS = 15.0

_AUTH = "auth_error"
_UNAVAILABLE = "unavailable"
_TIMEOUT = "timeout"
_HTTP = "http_error"
_NOT_FOUND = "not_found"
_VALIDATION = "validation"


def lookup_incidents(
    *,
    action: str,
    ticket_id: str | None = None,
    status: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    """Call the incident tool and return the shape the graph already stores."""
    called = call_incident_tool(
        action=action,
        ticket_id=ticket_id,
        status=status,
        category=category,
    )
    return _as_lookup(called)


def call_incident_tool(
    *,
    action: str | None = None,
    ticket_id: str | None = None,
    status: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    """Open an MCP session, load tools, optionally call one, then disconnect."""
    return asyncio.run(
        _call(
            action=action,
            ticket_id=ticket_id,
            status=status,
            category=category,
        )
    )


async def _call(
    *,
    action: str | None,
    ticket_id: str | None,
    status: str | None,
    category: str | None,
) -> dict[str, Any]:
    url = os.environ.get("MCP_SERVER_URL", "").strip()
    if not url:
        return {"tools": [], "payload": None, "error": _UNAVAILABLE}
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langchain_mcp_adapters.tools import load_mcp_tools

    headers: dict[str, str] = {}
    token = os.environ.get("MCP_ACCESS_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    client = MultiServerMCPClient(
        {
            _SERVER_NAME: {
                "transport": "streamable_http",
                "url": url,
                "headers": headers,
                "timeout": _timeout_seconds(),
            }
        }
    )
    try:
        async with client.session(_SERVER_NAME) as session:
            tools = await load_mcp_tools(session)
            names = sorted(tool.name for tool in tools)
            if action is None:
                return {"tools": names, "payload": None, "error": None}
            match = next((tool for tool in tools if tool.name == _TOOL_NAME), None)
            if match is None:
                return {"tools": names, "payload": None, "error": _HTTP}
            arguments = _arguments(
                action=action,
                ticket_id=ticket_id,
                status=status,
                category=category,
            )
            raw = await match.ainvoke(arguments)
    except Exception as exc:
        return {"tools": [], "payload": None, "error": _classify(exc)}
    return {"tools": names, "payload": _parse(raw), "error": None}


def _arguments(
    *,
    action: str,
    ticket_id: str | None,
    status: str | None,
    category: str | None,
) -> dict[str, str]:
    arguments = {"action": action}
    if ticket_id:
        arguments["ticket_id"] = ticket_id
    if status:
        arguments["status"] = status
    if category:
        arguments["category"] = category
    return arguments


def _timeout_seconds() -> float:
    raw = os.environ.get("MCP_CLIENT_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS
    if value <= 0:
        return _DEFAULT_TIMEOUT_SECONDS
    return value


def _classify(exc: BaseException) -> str:
    if isinstance(exc, BaseExceptionGroup):
        kinds = {_classify(item) for item in exc.exceptions}
        for kind in (_AUTH, _UNAVAILABLE, _TIMEOUT, _HTTP):
            if kind in kinds:
                return kind
    text = f"{type(exc).__name__} {exc}".casefold()
    if "auth_missing_token" in text or "auth_invalid_token" in text or " 401" in text or "unauthorized" in text:
        return _AUTH
    if "timeout" in text or "timed out" in text:
        return _TIMEOUT
    if "connect" in text or "connection refused" in text or "all connection attempts failed" in text:
        return _UNAVAILABLE
    return _HTTP


def _parse(raw: Any) -> Any:
    if isinstance(raw, tuple) and raw:
        raw = raw[0]
    if isinstance(raw, str):
        return _json_or_message(raw)
    if isinstance(raw, list):
        texts: list[str] = []
        for block in raw:
            if isinstance(block, str):
                texts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                texts.append(block["text"])
        if len(texts) == 1:
            return _json_or_message(texts[0])
        return {"message": "\n".join(texts)}
    if isinstance(raw, dict):
        return raw
    return {"message": "The MCP tool returned an unreadable result."}


def _json_or_message(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"message": text}


def _as_lookup(called: dict[str, Any]) -> dict[str, Any]:
    error = called.get("error")
    if error in {_AUTH, _UNAVAILABLE, _TIMEOUT, _HTTP}:
        return {"found": False, "incidents": [], "error": error, "message": None}
    payload = called.get("payload")
    if not isinstance(payload, dict):
        return {"found": False, "incidents": [], "error": _HTTP, "message": None}
    if payload.get("error_code"):
        message = str(payload.get("message") or "")
        if message == "Incident not found":
            return {"found": False, "incidents": [], "error": _NOT_FOUND, "message": message}
        if "timeout" in message.casefold():
            return {"found": False, "incidents": [], "error": _TIMEOUT, "message": message}
        if payload.get("error_code") == "VALIDATION_ERROR":
            return {"found": False, "incidents": [], "error": _VALIDATION, "message": message}
        return {"found": False, "incidents": [], "error": _HTTP, "message": message}
    if isinstance(payload.get("incident"), dict):
        return {
            "found": True,
            "incidents": [_present(payload["incident"])],
            "error": None,
            "message": None,
        }
    rows = payload.get("incidents")
    if isinstance(rows, list):
        if not rows:
            return {"found": False, "incidents": [], "error": _NOT_FOUND, "message": None}
        return {
            "found": True,
            "incidents": [_present(row) for row in rows if isinstance(row, dict)],
            "error": None,
            "message": None,
        }
    return {"found": False, "incidents": [], "error": _HTTP, "message": None}


def _present(row: dict[str, Any]) -> dict[str, Any]:
    def text(value: Any) -> Any:
        if value is None:
            return NOT_RECORDED
        return value

    score = row.get("satisfaction_score")
    return {
        "incident_id": row.get("incident_id"),
        "date": row.get("date"),
        "location_id": text(row.get("location_id")),
        "category": text(row.get("category")),
        "description": text(row.get("description")),
        "status": row.get("status"),
        "customer_id": text(row.get("customer_id")),
        "satisfaction_score": NOT_RECORDED if score is None else score,
        "reporter_id": row.get("reporter_id"),
    }
