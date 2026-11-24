"""Support-agent incident operations through the MCP server."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "services" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp_stack import ensure_stack  # noqa: E402
from services.agent.graph import agent_graph  # noqa: E402
from services.agent.mcp_incidents import call_incident_tool  # noqa: E402
from services.agent.tracing import invoke_config, read_trace  # noqa: E402

_TICKET = "What's the status of BRS-000012?"
_CREATE = "The incidents API exposes read routes only. Create was not sent."
_UPDATE = (
    "The incidents API has no status-update route. The requested transition was not sent."
)
_AUTH = (
    "I couldn't confirm that incident right now. "
    "The MCP server rejected the access token."
)
_DOWN = (
    "I couldn't confirm that incident right now. "
    "The MCP server is unavailable."
)


@pytest.fixture(scope="module")
def live_mcp(tmp_path_factory: pytest.TempPathFactory):
    db_path = tmp_path_factory.mktemp("mcp-agent") / "suppliers.json"
    return ensure_stack(db_path)


def _run(question: str, **extra: object) -> dict:
    trace_id = f"run-mcp-{uuid.uuid4().hex[:8]}"
    agent_graph.invoke({"question": question, **extra}, invoke_config(trace_id))
    return read_trace(trace_id)


def test_mcp_connection_discovers_tools(live_mcp) -> None:
    del live_mcp
    discovered = call_incident_tool(action=None)
    assert discovered["error"] is None
    assert "manage_incident_ticket" in discovered["tools"]
    assert "query_inventory" in discovered["tools"]


def test_ticket_lookup_through_the_agent(live_mcp) -> None:
    del live_mcp
    trace = _run(_TICKET)
    assert trace["route"] == "tool"
    assert trace["tool_outcome"] == "success"
    assert "lookup_ticket" in [step["node"] for step in trace["steps"]]
    assert "status: OPEN" in trace["answer"]
    assert "category: CUSTOMER_COMPLAINT" in trace["answer"]


def test_ticket_creation_through_the_agent(live_mcp) -> None:
    del live_mcp
    trace = _run(_TICKET, incident_action="create")
    assert trace["tool_outcome"] == "validation"
    assert trace["answer"] == _CREATE
    assert "status: OPEN" not in trace["answer"]


def test_ticket_status_update_through_the_agent(live_mcp) -> None:
    del live_mcp
    trace = _run(
        _TICKET,
        incident_action="update",
        incident_target_status="CLOSED",
    )
    assert trace["tool_outcome"] == "validation"
    assert trace["answer"] == _UPDATE
    assert "status: CLOSED" not in trace["answer"]


def test_authentication_failure(live_mcp, monkeypatch: pytest.MonkeyPatch) -> None:
    del live_mcp
    monkeypatch.setenv("MCP_ACCESS_TOKEN", "not-a-jwt")
    trace = _run(_TICKET)
    assert trace["tool_outcome"] == "auth_error"
    assert trace["answer"] == _AUTH
    assert "not-a-jwt" not in trace["answer"]
    assert "status: OPEN" not in trace["answer"]


def test_mcp_server_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:1/mcp")
    monkeypatch.delenv("MCP_ACCESS_TOKEN", raising=False)
    trace = _run(_TICKET)
    assert trace["tool_outcome"] == "unavailable"
    assert trace["answer"] == _DOWN
    assert "status: OPEN" not in trace["answer"]
