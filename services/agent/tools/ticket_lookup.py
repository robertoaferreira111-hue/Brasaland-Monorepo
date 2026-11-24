"""Incident id shape used by the router.

Incident records are not read here. The support agent loads them through the
MCP server in `services.agent.mcp_incidents`.
"""

from __future__ import annotations

import re

_BARE_ID = re.compile(r"^(?:BRS-)?(\d{1,6})$", re.IGNORECASE)


def normalize_incident_id(value: str | int) -> str | None:
    """Return ``BRS-######`` or None when the value is not that id shape."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        if value < 0 or value > 999_999:
            return None
        return f"BRS-{value:06d}"
    match = _BARE_ID.fullmatch(value.strip())
    if match is None:
        return None
    return f"BRS-{int(match.group(1)):06d}"
