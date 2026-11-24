"""Receive, route, retrieve, look up a ticket, and answer.

RAG-only runs keep the Part 1 step list. route_intent still runs, and it
writes a trace step only when the route is the ticket tool or both. Ticket
reads go through the MCP server. A ticket failure becomes an answer. It does
not raise and it does not invent a status.
"""

from __future__ import annotations

import data.pipelines.rag as rag

from services.agent.routing import decide_route
from services.agent.state import AgentState

_EMPTY_QUESTION = "Question is empty."
_NOT_FOUND = "I couldn't find incident {incident_id}."
_NOT_FOUND_FILTER = "I couldn't find an incident matching that request."
_TIMEOUT = "I couldn't confirm that incident right now. The lookup timed out."
_HTTP_ERROR = (
    "I couldn't confirm that incident right now. "
    "The incident service returned an error."
)
_AUTH_ERROR = (
    "I couldn't confirm that incident right now. "
    "The MCP server rejected the access token."
)
_UNAVAILABLE = (
    "I couldn't confirm that incident right now. "
    "The MCP server is unavailable."
)
_MANUALS_UNCHECKED = "I couldn't check the Brasaland manuals for this question."
_MANUALS_UNWRITTEN = "I couldn't write the manual answer for this question."
_FIELDS = (
    "status",
    "date",
    "location_id",
    "category",
    "description",
    "customer_id",
    "satisfaction_score",
    "reporter_id",
)


def _step(node: str, order: int, output_summary: str) -> dict:
    return {"node": node, "order": order, "output_summary": output_summary}


def _next_order(state: AgentState) -> int:
    steps = state.get("trace_steps") or []
    if not steps:
        return 1
    return max(int(step.get("order", 0)) for step in steps) + 1


def receive_question(state: AgentState) -> dict:
    raw = state.get("question", "")
    question = raw.strip() if isinstance(raw, str) else ""
    if not question:
        return {
            "question": "",
            "error": _EMPTY_QUESTION,
            "trace_steps": [_step("receive_question", 1, "empty question")],
        }
    return {
        "question": question,
        "error": None,
        "trace_steps": [_step("receive_question", 1, "question accepted")],
    }


def after_receive(state: AgentState) -> str:
    if state.get("error") or not str(state.get("question", "")).strip():
        return "end"
    return "route_intent"


def route_intent(state: AgentState) -> dict:
    decision = decide_route(str(state.get("question", "")))
    update: dict = {
        "route": decision.route,
        "route_rationale": decision.rationale,
        "incident_id": decision.incident_id,
        "incident_status": decision.status,
        "incident_category": decision.category,
        "error": None,
    }
    if decision.route != "rag":
        update["trace_steps"] = [
            _step(
                "route_intent",
                _next_order(state),
                f"route={decision.route}; {decision.rationale}",
            )
        ]
    return update


def after_route(state: AgentState) -> str:
    if state.get("route") in {"tool", "both"}:
        return "lookup_ticket"
    return "retrieve"


def lookup_ticket_node(state: AgentState) -> dict:
    from services.agent.mcp_incidents import lookup_incidents

    incident_id = state.get("incident_id")
    action = state.get("incident_action") or ("get_status" if incident_id else "list")
    status = state.get("incident_status")
    if action == "update":
        status = state.get("incident_target_status", status)
    result = lookup_incidents(
        action=str(action),
        ticket_id=incident_id,
        status=status,
        category=state.get("incident_category"),
    )
    outcome = "success" if result["found"] else (result["error"] or "http_error")
    return {
        "tool_results": [result],
        "error": None,
        "trace_steps": [
            _step("lookup_ticket", _next_order(state), f"outcome={outcome}")
        ],
    }


def after_lookup(state: AgentState) -> str:
    if _tool_found(state):
        if state.get("route") == "both":
            return "retrieve"
        return "synthesize_answer"
    return "handle_tool_failure"


def handle_tool_failure(state: AgentState) -> dict:
    text = _failure_text(state)
    return {
        "tool_answer": text,
        "error": None,
        "trace_steps": [
            _step(
                "handle_tool_failure",
                _next_order(state),
                f"outcome={_tool_outcome(state)}",
            )
        ],
    }


def after_failure(state: AgentState) -> str:
    if state.get("route") == "both":
        return "retrieve"
    return "synthesize_answer"


def retrieve_node(state: AgentState) -> dict:
    try:
        context = rag.retrieve(state["question"])
    except Exception as exc:
        return {
            "retrieved_context": None,
            "error": f"Retrieval failed: {exc}",
            "trace_steps": [_step("retrieve", _next_order(state), "retrieval failed")],
        }
    if not context:
        return {
            "retrieved_context": [],
            "answer": rag._NOT_ENOUGH,
            "error": None,
            "trace_steps": [
                _step("retrieve", _next_order(state), "0 chunks above threshold")
            ],
        }
    return {
        "retrieved_context": context,
        "error": None,
        "trace_steps": [
            _step(
                "retrieve",
                _next_order(state),
                f"{len(context)} chunk{'s' if len(context) != 1 else ''} above threshold",
            )
        ],
    }


def after_retrieve(state: AgentState) -> str:
    failed = bool(state.get("error")) or not state.get("retrieved_context")
    if state.get("route") == "both" and failed:
        return "synthesize_answer"
    if failed:
        return "end"
    return "query"


def query_node(state: AgentState) -> dict:
    context = state.get("retrieved_context") or []
    try:
        answer = rag.generate_answer(state["question"], context)
    except Exception as exc:
        return {
            "error": f"Generation failed: {exc}",
            "trace_steps": [_step("query", _next_order(state), "generation failed")],
        }
    return {
        "answer": answer,
        "error": None,
        "trace_steps": [_step("query", _next_order(state), "answer generated")],
    }


def after_query(state: AgentState) -> str:
    if state.get("error") and state.get("route") != "both":
        return "end"
    return "synthesize_answer"


def synthesize_answer(state: AgentState) -> dict:
    route = state.get("route")
    if route == "rag":
        answer = str(state.get("answer") or "")
        return {
            "final_answer": answer,
            "trace_steps": [
                _step("synthesize_answer", _next_order(state), "manual answer kept")
            ],
        }
    tool_text = state.get("tool_answer") or _format_results(state.get("tool_results"))
    if route == "both":
        answer = _both_answer(tool_text, state)
        summary = "ticket result and manuals"
    else:
        answer = tool_text
        summary = "ticket result only"
    return {
        "answer": answer,
        "final_answer": answer,
        "error": None,
        "trace_steps": [_step("synthesize_answer", _next_order(state), summary)],
    }


def _tool_found(state: AgentState) -> bool:
    results = state.get("tool_results") or []
    if not results:
        return False
    return results[-1].get("found") is True


def _tool_outcome(state: AgentState) -> str:
    results = state.get("tool_results") or []
    if not results:
        return "http_error"
    last = results[-1]
    if last.get("found") is True:
        return "success"
    error = last.get("error")
    if error in {"timeout", "not_found", "http_error", "auth_error", "unavailable", "validation"}:
        return str(error)
    return "http_error"


def _failure_text(state: AgentState) -> str:
    outcome = _tool_outcome(state)
    if outcome == "timeout":
        return _TIMEOUT
    if outcome == "auth_error":
        return _AUTH_ERROR
    if outcome == "unavailable":
        return _UNAVAILABLE
    if outcome == "validation":
        results = state.get("tool_results") or []
        message = results[-1].get("message") if results else None
        if message:
            return str(message)
        return _HTTP_ERROR
    if outcome == "http_error":
        return _HTTP_ERROR
    incident_id = state.get("incident_id")
    if incident_id:
        return _NOT_FOUND.format(incident_id=incident_id)
    return _NOT_FOUND_FILTER


def _format_results(results: list[dict] | None) -> str:
    rows: list[dict] = []
    for result in results or []:
        rows.extend(result.get("incidents") or [])
    if not rows:
        return _NOT_FOUND_FILTER
    blocks = [_format_incident(row) for row in rows]
    if len(blocks) == 1:
        return blocks[0]
    return f"{len(blocks)} incidents matched.\n\n" + "\n\n".join(blocks)


def _format_incident(row: dict) -> str:
    lines = [f"Incident {row.get('incident_id')}:"]
    for key in _FIELDS:
        lines.append(f"{key}: {row.get(key)}")
    return "\n".join(lines)


def _both_answer(tool_text: str, state: AgentState) -> str:
    error = str(state.get("error") or "")
    if error.startswith("Retrieval failed"):
        manuals = _MANUALS_UNCHECKED
    elif error.startswith("Generation failed"):
        manuals = _MANUALS_UNWRITTEN
    elif state.get("answer"):
        manuals = f"From the manuals: {state['answer']}"
    else:
        manuals = _MANUALS_UNCHECKED
    return f"{tool_text}\n\n{manuals}"
