"""Register each tool module on one FastMCP instance."""

from __future__ import annotations

from fastmcp import FastMCP
from mcpauth import MCPAuth

from company_tools.config import Settings
from company_tools.tools.incidents import register as register_incidents
from company_tools.tools.inventory import register as register_inventory


def register_tools(mcp: FastMCP, settings: Settings, mcp_auth: MCPAuth) -> None:
    register_incidents(mcp, settings, mcp_auth)
    register_inventory(mcp, settings, mcp_auth)
