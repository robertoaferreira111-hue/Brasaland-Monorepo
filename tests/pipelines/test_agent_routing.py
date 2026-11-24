"""Routing decisions and traces for the ticket tool.

Decision tests do not call the incident service. Trace tests call the real
lookup. The RAG-only trace calls the real retrieve step. A retrieval error, a
stop when nothing is above the threshold, and an answer from query are
all accepted. This file does not treat any of those as a grounded answer.
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

from mcp_stack import ensure_stack  # noqa: E402
from services.agent.graph import agent_graph  # noqa: E402
from services.agent.routing import decide_route  # noqa: E402
from services.agent.tracing import invoke_config, read_trace  # noqa: E402

_FAQ = "how many points do I need for Gold tier?"
_WASTE = "What categories of product waste must every location log?"
_WIFI = "What is the wifi password for the Medellín office?"
_REFUND = "What is the refund policy for delayed shipments?"
_TICKET = "What's the status of BRS-000012?"
_BOTH = "What should we do about the refund policy for incident BRS-000012?"


def test_named_id_routes_to_the_ticket_tool() -> None:
    decision = decide_route(_TICKET)
    assert decision.route == "tool"
    assert decision.incident_id == "BRS-000012"
    assert decision.status is None
    assert decision.category is None
    assert "manuals" in decision.rationale


def test_bare_incident_number_uses_the_csv_id() -> None:
    decision = decide_route("incident 12")
    assert decision.route == "tool"
    assert decision.incident_id == "BRS-000012"
    lowered = decide_route("ticket #7")
    assert lowered.incident_id == "BRS-000007"


def test_policy_questions_stay_on_the_manuals() -> None:
    for question in (_FAQ, _WASTE, _WIFI, _REFUND, "What time do you open?"):
        decision = decide_route(question)
        assert decision.route == "rag", question
        assert decision.incident_id is None
        assert decision.status is None
        assert decision.category is None


def test_filters_apply_when_no_id_is_named() -> None:
    decision = decide_route("list open incidents")
    assert decision.route == "tool"
    assert decision.incident_id is None
    assert decision.status == "OPEN"
    assert decision.category is None
    food = decide_route("closed food quality incidents")
    assert food.route == "tool"
    assert food.status == "CLOSED"
    assert food.category == "FOOD_QUALITY"


def test_procedure_and_an_id_use_both_in_tool_then_manual_order() -> None:
    decision = decide_route(_BOTH)
    assert decision.route == "both"
    assert decision.incident_id == "BRS-000012"
    assert decision.status is None
    assert "ticket tool, then manuals" in decision.rationale


def test_incident_mention_without_a_lookup_stays_on_the_manuals() -> None:
    decision = decide_route("tell me about the incident yesterday")
    assert decision.route == "rag"
    assert "no ticket lookup" in decision.rationale


def test_staff_training_is_not_a_staff_incident_filter() -> None:
    decision = decide_route("staff training procedure")
    assert decision.route == "rag"
    assert decision.category is None


def test_only_the_first_id_is_looked_up() -> None:
    decision = decide_route("compare BRS-000001 and BRS-000002")
    assert decision.route == "tool"
    assert decision.incident_id == "BRS-000001"
    assert "BRS-000002" in decision.rationale
    assert "not looked up" in decision.rationale


def test_two_statuses_are_not_applied_as_one_filter() -> None:
    decision = decide_route("open and closed incidents")
    assert decision.route == "tool"
    assert decision.status is None
    assert "More than one status" in decision.rationale


def test_the_same_question_always_routes_the_same_way() -> None:
    assert decide_route(_BOTH) == decide_route(_BOTH)
    assert decide_route(_REFUND) == decide_route(_REFUND)


@pytest.fixture(scope="module")
def live_mcp(tmp_path_factory: pytest.TempPathFactory):
    db_path = tmp_path_factory.mktemp("route-incidents") / "suppliers.json"
    return ensure_stack(db_path)


def _run(question: str) -> dict:
    trace_id = f"run-route-{uuid.uuid4().hex[:8]}"
    agent_graph.invoke({"question": question}, invoke_config(trace_id))
    return read_trace(trace_id)


def _nodes(trace: dict) -> list[str]:
    return [step["node"] for step in trace["steps"]]


def test_seeded_ticket_trace(live_mcp) -> None:
    del live_mcp
    trace = _run(_TICKET)
    assert trace["route"] == "tool"
    assert trace["incident_id"] == "BRS-000012"
    assert trace["tool_outcome"] == "success"
    assert trace["sources"] == ["tool"]
    nodes = _nodes(trace)
    assert nodes.index("route_intent") < nodes.index("lookup_ticket")
    assert "retrieve" not in nodes
    assert "query" not in nodes
    answer = trace["answer"]
    assert "status: OPEN" in answer
    assert "category: CUSTOMER_COMPLAINT" in answer
    assert "satisfaction_score: not recorded" in answer
    assert "date: 2024-01-02" in answer
    assert "status: CLOSED" not in answer


def test_missing_id_trace_is_not_found(live_mcp) -> None:
    del live_mcp
    trace = _run("incident 482")
    assert trace["route"] == "tool"
    assert trace["incident_id"] == "BRS-000482"
    assert trace["tool_outcome"] == "not_found"
    assert trace["sources"] == ["tool"]
    assert "retrieve" not in _nodes(trace)
    assert trace["answer"] == "I couldn't find incident BRS-000482."
    assert "OPEN" not in trace["answer"]
    assert "CLOSED" not in trace["answer"]


def test_unavailable_mcp_does_not_invent_a_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SERVER_URL", "http://127.0.0.1:1/mcp")
    trace = _run(_TICKET)
    assert trace["tool_outcome"] == "unavailable"
    assert "handle_tool_failure" in _nodes(trace)
    assert "retrieve" not in _nodes(trace)
    assert trace["answer"] == (
        "I couldn't confirm that incident right now. "
        "The MCP server is unavailable."
    )
    assert "OPEN" not in trace["answer"]
    assert "CLOSED" not in trace["answer"]


def test_rag_only_trace_uses_the_real_retrieve() -> None:
    """The refund question stays on the manuals.

    Part 1 may then stop with a retrieval error, stop because nothing is
    above the threshold, or continue to query. This assertion does not
    require query. It fails if the question is sent to the ticket tool.
    """
    trace = _run(_REFUND)
    nodes = _nodes(trace)
    assert trace["route"] == "rag"
    assert "No incident id" in trace["route_rationale"]
    assert "no incident filter" in trace["route_rationale"]
    assert trace["incident_id"] is None
    assert trace["incident_status"] is None
    assert trace["incident_category"] is None
    assert "lookup_ticket" not in nodes
    assert "handle_tool_failure" not in nodes
    assert trace["sources"] == ["rag"]
    assert trace["tool_outcome"] is None
    assert "retrieve" in nodes
    if "query" in nodes:
        assert nodes.index("retrieve") < nodes.index("query")
    if trace["error"]:
        assert str(trace["error"]).startswith(("Retrieval failed", "Generation failed"))
    else:
        assert trace["answer"]
