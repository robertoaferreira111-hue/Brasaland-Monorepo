"""Evals for the support-agent graph.

Node order and the error paths assert against checkpoint traces. The grounded
answer calls the real retrieve and generate_answer steps only when RAG
credentials are configured. Otherwise that eval is skipped and is not a pass.

company-BRIEFING.md defines Waste Cost per Location as loss to expired
product, kitchen error, or theft. The indexed waste manual uses the same
phrase "kitchen error". Gold tier is not in that briefing.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

import data.pipelines.rag as rag  # noqa: E402
from services.agent.graph import agent_graph  # noqa: E402
from services.agent.tracing import invoke_config, read_trace  # noqa: E402

_FAQ = "how many points do I need for Gold tier?"
_WASTE_QUESTION = "What categories of product waste must every location log?"
_BRIEFING_FACT = "kitchen error"
_NO_CONTEXT = "What is the wifi password for the Medellín office?"


def _trace_id(name: str) -> str:
    return f"run-eval-{name}-{uuid.uuid4().hex[:8]}"


def _nodes(trace_id: str) -> list[str]:
    return [step["node"] for step in read_trace(trace_id)["steps"]]


def _missing_rag_credentials() -> str | None:
    rag._load_env()
    required = (
        "EMBEDDING_MODEL",
        "EMBEDDING_API_KEY",
        "EMBEDDING_BASE_URL",
        "GENERATION_MODEL",
    )
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if not missing:
        return None
    return (
        "Live grounded eval skipped: RAG credentials are not configured "
        f"({', '.join(missing)} unset). This skip is not a pass."
    )


def test_node_order_retrieve_before_query(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def retrieve(question: str, **_kwargs: object) -> list[dict]:
        del question
        calls.append("retrieve")
        return [
            {
                "text": "Gold (50+ points): 15% permanent discount",
                "source_document": "loyalty-program",
                "section": "Program tiers",
            }
        ]

    def generate_answer(question: str, context: list[dict]) -> str:
        del question
        calls.append("generate_answer")
        assert context and context[0]["section"] == "Program tiers"
        return "Gold tier starts at 50 points."

    def query(question: str) -> str:
        del question
        calls.append("query")
        raise AssertionError("query() must not run")

    monkeypatch.setattr(rag, "retrieve", retrieve)
    monkeypatch.setattr(rag, "generate_answer", generate_answer)
    monkeypatch.setattr(rag, "query", query)

    trace_id = _trace_id("order")
    agent_graph.invoke({"question": _FAQ}, invoke_config(trace_id))
    nodes = _nodes(trace_id)
    assert nodes.index("retrieve") < nodes.index("query")
    assert calls == ["retrieve", "generate_answer"]


def test_grounded_answer_contains_briefing_waste_fact() -> None:
    reason = _missing_rag_credentials()
    if reason:
        pytest.skip(reason)
    trace_id = _trace_id("grounded")
    result = agent_graph.invoke({"question": _WASTE_QUESTION}, invoke_config(trace_id))
    assert not result.get("error"), result.get("error")
    answer = result.get("answer") or ""
    assert answer.strip()
    assert _BRIEFING_FACT in answer.casefold()
    nodes = _nodes(trace_id)
    assert nodes.index("retrieve") < nodes.index("query")


def test_empty_question_ends_without_query() -> None:
    trace_id = _trace_id("empty")
    result = agent_graph.invoke({"question": "   "}, invoke_config(trace_id))
    assert result.get("error") == "Question is empty."
    nodes = _nodes(trace_id)
    assert nodes == ["receive_question"]
    assert "query" not in nodes


def test_no_context_skips_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def retrieve(question: str, **_kwargs: object) -> list[dict]:
        del question
        calls.append("retrieve")
        return []

    def generate_answer(question: str, context: list[dict]) -> str:
        del question, context
        calls.append("generate_answer")
        raise AssertionError("generation must not run without context")

    def query(question: str) -> str:
        del question
        calls.append("query")
        raise AssertionError("query() must not run")

    monkeypatch.setattr(rag, "retrieve", retrieve)
    monkeypatch.setattr(rag, "generate_answer", generate_answer)
    monkeypatch.setattr(rag, "query", query)

    trace_id = _trace_id("no-context")
    result = agent_graph.invoke({"question": _NO_CONTEXT}, invoke_config(trace_id))
    assert result.get("answer") == rag._NOT_ENOUGH
    assert not result.get("error")
    nodes = _nodes(trace_id)
    assert nodes == ["receive_question", "retrieve"]
    assert calls == ["retrieve"]
