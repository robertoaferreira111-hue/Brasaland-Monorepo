"""Support-agent graph. Compiled once when this module is imported."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from services.agent.nodes import (
    after_receive,
    after_retrieve,
    query_node,
    receive_question,
    retrieve_node,
)
from services.agent.state import AgentState


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
    return builder.compile(checkpointer=MemorySaver())


agent_graph = build_agent_graph()
