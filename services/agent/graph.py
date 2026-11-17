"""Support-agent graph. Compiled once when this module is imported.

Compilation checks that every node can be reached from the entry point, every
node can reach END, and every edge names a real target. A broken graph raises
before the module finishes importing, so the API does not start.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from services.agent.nodes import (
    after_receive,
    after_retrieve,
    query_node,
    receive_question,
    retrieve_node,
)
from services.agent.state import AgentState


def _adjacency(builder: StateGraph) -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {}

    def add(source: str, target: str) -> None:
        edges.setdefault(source, set()).add(target)

    for source, target in builder.edges:
        add(source, target)
    for starts, target in getattr(builder, "waiting_edges", ()):
        for source in starts:
            add(source, target)
    for source, branches in builder.branches.items():
        for branch in branches.values():
            if branch.ends is None:
                raise ValueError(
                    f"Node '{source}' has a conditional edge with no declared targets."
                )
            for target in branch.ends.values():
                add(source, target)
    return edges


def _reaches_end(node: str, edges: dict[str, set[str]], seen: set[str]) -> bool:
    if node in seen:
        return False
    seen.add(node)
    for target in edges.get(node, ()):
        if target == END or _reaches_end(target, edges, seen):
            return True
    return False


def require_valid_structure(builder: StateGraph) -> None:
    """Raise ValueError when the builder cannot run from START to END."""
    edges = _adjacency(builder)
    known = set(builder.nodes) | {END}
    for source, targets in sorted(edges.items()):
        for target in sorted(targets):
            if target not in known:
                raise ValueError(
                    f"Edge from '{source}' targets unknown node '{target}'."
                )

    reachable: set[str] = set()
    pending = [target for target in edges.get(START, ()) if target != END]
    while pending:
        node = pending.pop()
        if node in reachable:
            continue
        reachable.add(node)
        for target in edges.get(node, ()):
            if target != END and target not in reachable:
                pending.append(target)
    for name in sorted(builder.nodes):
        if name not in reachable:
            raise ValueError(f"Node '{name}' is unreachable from the entry point.")

    for name in sorted(builder.nodes):
        if not _reaches_end(name, edges, set()):
            raise ValueError(f"Node '{name}' has no path to END.")


def compile_support_graph(builder: StateGraph):
    require_valid_structure(builder)
    return builder.compile(checkpointer=MemorySaver())


def build_agent_graph():
    builder = StateGraph(AgentState)
    builder.add_node("receive_question", receive_question)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("query", query_node)
    builder.set_entry_point("receive_question")
    builder.add_conditional_edges(
        "receive_question",
        after_receive,
        {"retrieve": "retrieve", "end": END},
    )
    builder.add_conditional_edges(
        "retrieve",
        after_retrieve,
        {"query": "query", "end": END},
    )
    builder.add_edge("query", END)
    return compile_support_graph(builder)


agent_graph = build_agent_graph()
