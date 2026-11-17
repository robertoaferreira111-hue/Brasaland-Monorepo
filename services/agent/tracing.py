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
    return {
        "trace_id": trace_id,
        "steps": steps,
        "answer": values.get("answer"),
        "error": values.get("error"),
        "checkpoints": checkpoints,
    }
