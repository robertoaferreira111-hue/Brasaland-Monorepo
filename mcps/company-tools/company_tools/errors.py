"""Error values the MCP server returns to clients."""

from __future__ import annotations

AUTH_MISSING_TOKEN = "AUTH_MISSING_TOKEN"
AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
INSUFFICIENT_SCOPE = "INSUFFICIENT_SCOPE"
INVENTORY_WRITE_FORBIDDEN = "INVENTORY_WRITE_FORBIDDEN"
VALIDATION_ERROR = "VALIDATION_ERROR"
UPSTREAM_ERROR = "UPSTREAM_ERROR"

AUTH_MISSING_TOKEN_MESSAGE = "An OAuth access token is required."
AUTH_INVALID_TOKEN_MESSAGE = "The OAuth access token is invalid or expired."
INSUFFICIENT_SCOPE_MESSAGE = (
    "The access token does not include the scope required for this operation."
)
INVENTORY_WRITE_MESSAGE = (
    "Inventory tool is read-only. Write operations are not permitted on this MCP server."
)


class ConfigurationError(Exception):
    """Required environment is missing or a value cannot be used."""

    def __init__(self, missing: list[str] | None = None, invalid: list[str] | None = None) -> None:
        self.missing = list(missing or [])
        self.invalid = list(invalid or [])
        parts: list[str] = []
        if self.missing:
            parts.append("missing " + ", ".join(self.missing))
        if self.invalid:
            parts.append("invalid " + ", ".join(self.invalid))
        super().__init__("; ".join(parts) or "configuration error")


def tool_error(code: str, message: str, tool: str) -> dict[str, str]:
    return {"error_code": code, "message": message, "tool": tool}
