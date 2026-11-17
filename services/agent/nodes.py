"""Receive, retrieve, and generate. Each node does one of those steps."""

from __future__ import annotations

import data.pipelines.rag as rag

from services.agent.state import AgentState

_EMPTY_QUESTION = "Question is empty."


def _step(node: str, order: int, output_summary: str) -> dict:
    return {"node": node, "order": order, "output_summary": output_summary}


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
    return "retrieve"


def retrieve_node(state: AgentState) -> dict:
    try:
        context = rag.retrieve(state["question"])
    except Exception as exc:
        return {
            "retrieved_context": None,
            "error": f"Retrieval failed: {exc}",
            "trace_steps": [_step("retrieve", 2, "retrieval failed")],
        }
    if not context:
        return {
            "retrieved_context": [],
            "answer": rag._NOT_ENOUGH,
            "error": None,
            "trace_steps": [_step("retrieve", 2, "0 chunks above threshold")],
        }
    return {
        "retrieved_context": context,
        "error": None,
        "trace_steps": [
            _step(
                "retrieve",
                2,
                f"{len(context)} chunk{'s' if len(context) != 1 else ''} above threshold",
            )
        ],
    }


def after_retrieve(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    if not state.get("retrieved_context"):
        return "end"
    return "query"


def query_node(state: AgentState) -> dict:
    context = state.get("retrieved_context") or []
    try:
        answer = rag.generate_answer(state["question"], context)
    except Exception as exc:
        return {
            "error": f"Generation failed: {exc}",
            "trace_steps": [_step("query", 3, "generation failed")],
        }
    return {
        "answer": answer,
        "error": None,
        "trace_steps": [_step("query", 3, "answer generated")],
    }
