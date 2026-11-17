"""Unit tests for Brasaland manual retrieval and answer generation.

Qdrant and the generation model are replaced in-process. These tests do not
open a network connection.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

import data.pipelines.rag as rag  # noqa: E402


def test_retrieve_filters_below_min_score(monkeypatch) -> None:
    seen: dict[str, int] = {}

    def fake_search(vector: list[float], k: int) -> list[dict]:
        seen["k"] = k
        assert vector == [0.1]
        return [
            {"score": 0.9, "payload": {"text": "a"}},
            {"score": 0.5, "payload": {"text": "b"}},
        ]

    monkeypatch.setattr(rag, "embed", lambda text: [0.1])
    monkeypatch.setattr(rag, "_search", fake_search)
    result = rag.retrieve("test", k=5, min_score=0.75)
    assert seen["k"] == 5
    assert len(result) == 1
    assert len(result) < 5
    assert result[0]["text"] == "a"


def test_retrieve_keeps_a_score_equal_to_min_score(monkeypatch) -> None:
    monkeypatch.setattr(rag, "embed", lambda text: [0.1])
    monkeypatch.setattr(
        rag,
        "_search",
        lambda vector, k: [
            {"score": 0.75, "payload": {"text": "kept"}},
            {"score": 0.749, "payload": {"text": "dropped"}},
        ],
    )
    result = rag.retrieve("test", k=2, min_score=0.75)
    assert [item["text"] for item in result] == ["kept"]


def test_query_returns_llm_output_not_raw_chunks(monkeypatch) -> None:
    chunk = {
        "text": "Gold (50+ points): 15% permanent discount",
        "source_document": "loyalty-program",
        "section": "Program tiers",
    }
    prompts: list[str] = []
    monkeypatch.setattr(rag, "retrieve", lambda question: [chunk])
    monkeypatch.setattr(rag, "_complete", lambda prompt: prompts.append(prompt) or "Sales answer")
    answer = rag.query("how many points do I need for Gold tier?")
    assert answer == "Sales answer"
    assert chunk["text"] not in answer
    assert chunk["text"] in prompts[0]


def test_query_empty_context_still_calls_the_llm(monkeypatch) -> None:
    prompts: list[str] = []
    monkeypatch.setattr(rag, "retrieve", lambda question: [])
    monkeypatch.setattr(
        rag,
        "_complete",
        lambda prompt: prompts.append(prompt) or rag._NOT_ENOUGH,
    )
    answer = rag.query("What is the wifi password for the Medellín office?")
    assert answer == rag._NOT_ENOUGH
    assert len(prompts) == 1
    assert "No relevant context was retrieved." in prompts[0]
    assert rag._NOT_ENOUGH in prompts[0]
