"""Support-agent helpers.

Incident records are loaded through `services.agent.mcp_incidents`.
This package only normalizes incident ids for the router.
"""

from services.agent.tools.ticket_lookup import normalize_incident_id

__all__ = ["normalize_incident_id"]
