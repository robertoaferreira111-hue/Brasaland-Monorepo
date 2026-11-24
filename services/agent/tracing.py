"""Read a finished run from the graph checkpointer.

The trace id is the checkpoint thread id. After invoke, read_trace returns
the nodes that ran, their order, and the summary each node wrote.
"""

from __future__ import annotations

import uuid

from services.agent.graph import agent_graph


def new_trace_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def invoke_config(trace_id: str) -> dict:
    return {"configurable": {"thread_id": trace_id}}


def read_trace(trace_id: str) -> dict:
    config = invoke_config(trace_id)
    snapshot = agent_graph.get_state(config)
    values = snapshot.values or {}
    steps = [dict(step) for step in values.get("trace_steps") or []]
    checkpoints = []
    for item in agent_graph.get_state_history(config):
        item_values = item.values or {}
        checkpoints.append(
            {
                "next": list(item.next),
                "nodes": [
                    step.get("node") for step in item_values.get("trace_steps") or []
                ],
            }
        )
    checkpoints.reverse()
    tool_outcome = _tool_outcome(values.get("tool_results"))
    sources: list[str] = []
    for step in steps:
        node = step.get("node")
        if node == "lookup_ticket" and "tool" not in sources:
            sources.append("tool")
        if node == "retrieve" and "rag" not in sources:
            sources.append("rag")
    return {
        "trace_id": trace_id,
        "steps": steps,
        "answer": values.get("answer"),
        "error": values.get("error"),
        "checkpoints": checkpoints,
        "route": values.get("route"),
        "route_rationale": values.get("route_rationale"),
        "incident_id": values.get("incident_id"),
        "incident_status": values.get("incident_status"),
        "incident_category": values.get("incident_category"),
        "tool_outcome": tool_outcome,
        "sources": sources,
        "final_answer": values.get("final_answer"),
    }


def _tool_outcome(results: object) -> str | None:
    if not isinstance(results, list) or not results:
        return None
    last = results[-1]
    if not isinstance(last, dict):
        return None
    if last.get("found") is True:
        return "success"
    error = last.get("error")
    if error in {"timeout", "not_found", "http_error", "auth_error", "unavailable", "validation"}:
        return str(error)
    return None
