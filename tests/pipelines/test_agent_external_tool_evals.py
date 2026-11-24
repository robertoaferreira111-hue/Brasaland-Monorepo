"""Routing evals for the support agent.

Ticket questions go through the MCP server. Manual questions stub retrieval
and generation. They do not call an embedding provider or Qdrant.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "services" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import data.pipelines.rag as rag  # noqa: E402

from mcp_stack import ensure_stack  # noqa: E402
from services.agent.graph import agent_graph  # noqa: E402
from services.agent.tracing import invoke_config, read_trace  # noqa: E402

_TICKET = "What's the status of BRS-000012?"
_REFUND = "What is the refund policy for delayed shipments?"
_BOTH = "What should we do about the refund policy for incident BRS-000012?"
_MANUAL_ANSWER = "Refunds for a delayed shipment follow the supplier ordering manual."
_STATUSES = ("OPEN", "CLOSED", "DISCARDED")
_CATEGORIES = (
    "CUSTOMER_COMPLAINT",
    "EQUIPMENT",
    "SUPPLY",
    "FOOD_QUALITY",
    "STAFF",
)


def _trace_id(name: str) -> str:
    return f"run-eval-route-{name}-{uuid.uuid4().hex[:8]}"


def _nodes(trace: dict) -> list[str]:
    return [step["node"] for step in trace["steps"]]


def _invoke(question: str) -> dict:
    trace_id = _trace_id("run")
    agent_graph.invoke({"question": question}, invoke_config(trace_id))
    return read_trace(trace_id)


@pytest.fixture(scope="module")
def live_mcp(tmp_path_factory: pytest.TempPathFactory):
    db_path = tmp_path_factory.mktemp("eval-incidents") / "suppliers.json"
    return ensure_stack(db_path)


def _stub_manuals(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def retrieve(question: str, **_kwargs: object) -> list[dict]:
        del question
        calls.append("retrieve")
        return [
            {
                "text": "Delayed shipments are recorded against the supplier order.",
                "source_document": "supplier-ordering",
                "section": "Delays",
            }
        ]

    def generate_answer(question: str, context: list[dict]) -> str:
        del question
        calls.append("generate_answer")
        assert context and context[0]["section"] == "Delays"
        return _MANUAL_ANSWER

    def query(question: str) -> str:
        del question
        calls.append("query")
        raise AssertionError("query() must not run")

    monkeypatch.setattr(rag, "retrieve", retrieve)
    monkeypatch.setattr(rag, "generate_answer", generate_answer)
    monkeypatch.setattr(rag, "query", query)
    return calls


def _forbid_incident_read(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from services.agent import mcp_incidents

    calls: list[str] = []

    def read(**kwargs):
        del kwargs
        calls.append("read")
        raise AssertionError("incident read must not run")

    monkeypatch.setattr(mcp_incidents, "lookup_incidents", read)
    return calls


def test_ticket_question_uses_the_tool_and_skips_rag(
    live_mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del live_mcp
    manual_calls = _stub_manuals(monkeypatch)
    trace = _invoke(_TICKET)
    nodes = _nodes(trace)
    assert trace["route"] == "tool"
    assert trace["incident_id"] == "BRS-000012"
    assert "lookup_ticket" in nodes
    assert "retrieve" not in nodes
    assert "query" not in nodes
    assert trace["sources"] == ["tool"]
    assert trace["tool_outcome"] == "success"
    assert manual_calls == []
    answer = trace["answer"]
    assert "status: OPEN" in answer
    assert "category: CUSTOMER_COMPLAINT" in answer
    assert "date: 2024-01-02" in answer
    assert "location_id: COL-10" in answer
    assert "satisfaction_score: not recorded" in answer
    assert "status: CLOSED" not in answer


def test_policy_question_uses_rag_and_does_not_read_incidents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manual_calls = _stub_manuals(monkeypatch)
    reads = _forbid_incident_read(monkeypatch)
    trace = _invoke(_REFUND)
    nodes = _nodes(trace)
    assert trace["route"] == "rag"
    assert trace["incident_id"] is None
    assert nodes.index("retrieve") < nodes.index("query")
    assert "lookup_ticket" not in nodes
    assert "handle_tool_failure" not in nodes
    assert trace["sources"] == ["rag"]
    assert trace["tool_outcome"] is None
    assert reads == []
    assert manual_calls == ["retrieve", "generate_answer"]
    assert trace["answer"] == _MANUAL_ANSWER


def test_tool_failure_does_not_invent_ticket_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:1/mcp")
    trace = _invoke(_TICKET)
    nodes = _nodes(trace)
    assert trace["route"] == "tool"
    assert "lookup_ticket" in nodes
    assert "handle_tool_failure" in nodes
    assert nodes.index("lookup_ticket") < nodes.index("handle_tool_failure")
    assert "retrieve" not in nodes
    assert trace["tool_outcome"] == "unavailable"
    assert "MCP server is unavailable" in trace["answer"]
    for word in (*_STATUSES, *_CATEGORIES, "2024-", "not recorded"):
        assert word not in trace["answer"]


def test_missing_id_is_not_found_without_an_invented_ticket(live_mcp) -> None:
    del live_mcp
    trace = _invoke("incident 482")
    assert trace["route"] == "tool"
    assert trace["incident_id"] == "BRS-000482"
    assert trace["tool_outcome"] == "not_found"
    assert "handle_tool_failure" in _nodes(trace)
    assert trace["answer"] == "I couldn't find incident BRS-000482."
    for word in (*_STATUSES, *_CATEGORIES, "2024-", "not recorded"):
        assert word not in trace["answer"]


def test_null_category_is_reported_as_not_recorded(live_mcp) -> None:
    del live_mcp
    trace = _invoke("What's the category of BRS-000049?")
    assert trace["route"] == "tool"
    assert trace["tool_outcome"] == "success"
    assert "retrieve" not in _nodes(trace)
    answer = trace["answer"]
    assert "category: not recorded" in answer
    assert "status: OPEN" in answer
    assert "location_id: COL-03" in answer
    assert "description: Incidencia sin categorizar reportada por supervisor" in answer
    assert "customer_id: not recorded" in answer
    assert "satisfaction_score: not recorded" in answer


def test_both_runs_the_ticket_tool_before_rag(
    live_mcp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del live_mcp
    manual_calls = _stub_manuals(monkeypatch)
    trace = _invoke(_BOTH)
    nodes = _nodes(trace)
    assert trace["route"] == "both"
    assert "ticket tool, then manuals" in trace["route_rationale"]
    assert nodes.index("lookup_ticket") < nodes.index("retrieve")
    assert nodes.index("retrieve") < nodes.index("query")
    assert trace["sources"] == ["tool", "rag"]
    assert trace["tool_outcome"] == "success"
    assert manual_calls == ["retrieve", "generate_answer"]
    assert "status: OPEN" in trace["answer"]
    assert f"From the manuals: {_MANUAL_ANSWER}" in trace["answer"]
