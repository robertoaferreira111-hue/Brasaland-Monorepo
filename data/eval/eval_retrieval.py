"""Measure Recall@3 and numeric faithfulness for the Brasaland manuals.

Run from the repo root after the four manuals are indexed in Qdrant and the
embedding and generation settings are in .env:

    uv run --project services/api python data/eval/eval_retrieval.py

Recall@3 calls retrieve(question, k=3, min_score=0). A question hits when any
returned payload has the source_document, section, and chunk_index recorded
in test-queries.json. Recall@3 is hits / total questions.

Faithfulness calls generate_answer with those same payloads. A digit token in
the answer is flagged when that token, ignoring commas and a trailing percent
sign, is not a digit token in the retrieved chunk text.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from data.pipelines.rag import generate_answer, retrieve  # noqa: E402

_QUERIES = Path(__file__).with_name("test-queries.json")
_NUMBER = re.compile(r"(?<!\d)\d[\d,]*(?:\.\d+)?%?(?!\d)")


def _tokens(text: str) -> list[str]:
    return [match.group(0).replace(",", "").removesuffix("%") for match in _NUMBER.finditer(text)]


def _missing_numbers(answer: str, chunks: list[dict]) -> list[str]:
    context = "\n".join(str(chunk.get("text", "")) for chunk in chunks)
    allowed = set(_tokens(context))
    missing: list[str] = []
    for token in _tokens(answer):
        if token not in allowed and token not in missing:
            missing.append(token)
    return missing


def _matches(payload: dict, expected: dict) -> bool:
    return (
        payload.get("source_document") == expected["source_document"]
        and payload.get("section") == expected["section"]
        and payload.get("chunk_index") == expected["chunk_index"]
    )


def main() -> None:
    questions = json.loads(_QUERIES.read_text(encoding="utf-8"))
    hits = 0
    rows: list[dict] = []
    for item in questions:
        payloads = retrieve(item["question"], k=3, min_score=0)
        hit = any(_matches(payload, item) for payload in payloads)
        hits += int(hit)
        answer = generate_answer(item["question"], payloads)
        missing = _missing_numbers(answer, payloads)
        top = [
            {
                "source_document": payload.get("source_document"),
                "section": payload.get("section"),
                "chunk_index": payload.get("chunk_index"),
            }
            for payload in payloads
        ]
        rows.append(
            {
                "question": item["question"],
                "expected": {
                    "source_document": item["source_document"],
                    "section": item["section"],
                    "chunk_index": item["chunk_index"],
                },
                "hit": hit,
                "top3": top,
                "answer": answer,
                "numbers_absent_from_chunks": missing,
            }
        )
    total = len(questions)
    report = {
        "recall_at_3": f"{hits}/{total}",
        "faithfulness_flags": sum(1 for row in rows if row["numbers_absent_from_chunks"]),
        "questions": rows,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
