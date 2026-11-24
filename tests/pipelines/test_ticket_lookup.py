"""Incident id normalization. Record reads go through the MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from services.agent.graph import agent_graph  # noqa: E402
from services.agent.tools.ticket_lookup import normalize_incident_id  # noqa: E402


def test_bare_number_and_prefixed_id() -> None:
    assert normalize_incident_id(1) == "BRS-000001"
    assert normalize_incident_id("brs-000044") == "BRS-000044"
    assert normalize_incident_id("ticket 482") is None
    assert normalize_incident_id(True) is None


def test_direct_lookup_is_not_a_second_incident_path() -> None:
    source = Path(
        _ROOT / "services" / "agent" / "tools" / "ticket_lookup.py"
    ).read_text()
    assert "get_incident" not in source
    assert "list_incidents" not in source
    assert "TinyDB" not in source


def test_graph_nodes_include_the_ticket_path() -> None:
    names = {name for name in agent_graph.nodes if not str(name).startswith("__")}
    assert names == {
        "receive_question",
        "route_intent",
        "retrieve",
        "query",
        "lookup_ticket",
        "handle_tool_failure",
        "synthesize_answer",
    }
