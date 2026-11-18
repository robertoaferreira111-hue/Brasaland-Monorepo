"""Support-agent tools.

Importing ``services.agent`` does not import this package. The Part 1 graph
stays on receive, retrieve, and query until a later phase wires a tool in.
"""

from services.agent.tools.ticket_lookup import TicketLookupOutput, lookup_ticket

__all__ = ["TicketLookupOutput", "lookup_ticket"]
