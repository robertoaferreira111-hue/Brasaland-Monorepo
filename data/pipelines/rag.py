"""Answer a location-manager question from the Brasaland manuals.

retrieve() embeds the question with data.process.rag.embed and returns
payload dicts. generate_answer() calls the generation model. query() is
retrieve() followed by generate_answer(). This module does not expose an
HTTP route.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from data.process.rag import COLLECTION, COMPANY, embed  # noqa: E402

# Cosine scores from pplx-embed-v1-0.6b on these manuals peak near 0.61.
# Correct sections scored 0.533 to 0.610. The next unrelated sections scored
# at most 0.331, and an off-topic question peaked at 0.196. 0.45 sits in
# that gap. The reference example of 0.75 filtered out every correct chunk.
DEFAULT_MIN_SCORE = 0.45

_NOT_ENOUGH = "There is not enough information in the Brasaland manuals to answer that."

_SYSTEM = f"""You are a trained salesperson at {COMPANY}. You are answering a location manager from Operations or Marketing. Be confident and correct. Answer in English.

Use only the retrieved context. Do not invent policies, prices, dishes, or procedures. If the context does not contain the answer, say: {_NOT_ENOUGH}

Do not include a percentage, an amount, or a weight in kilograms unless that exact number appears in the context. Keep US dollar and Colombian peso amounts exactly as written in the context. Do not convert currency.

For allergens, follow the manual wording in the context literally. Never say or imply "zero risk". The manual states that "Zero cross-contamination risk" is never guaranteed.

In the answer, name the source document and section you relied on."""


class AnswerError(RuntimeError):
    """The question cannot be answered from the generation model."""


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise AnswerError(
            "python-dotenv is not installed. Run this with: "
            "uv run --project services/api python data/pipelines/rag.py"
        ) from exc
    for path in (_REPO / ".env" / "local", _REPO / ".env", _REPO / "services" / "api" / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise AnswerError(f"{name} is not set. Add it to .env before generating an answer.")
    return value


def _qdrant_base() -> str:
    _load_env()
    return os.getenv("QDRANT_URL", "http://127.0.0.1:6333").strip().rstrip("/")


def _search(vector: list[float], k: int) -> list[dict[str, Any]]:
    """Return Qdrant hits as plain dicts with score and payload."""
    request = urllib.request.Request(
        f"{_qdrant_base()}/collections/{COLLECTION}/points/search",
        data=json.dumps({"vector": vector, "limit": k, "with_payload": True}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:400]
        raise AnswerError(f"Qdrant search failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise AnswerError(f"Qdrant is not reachable: {exc.reason}") from exc
    hits = []
    for item in body.get("result", []):
        payload = item.get("payload")
        if not isinstance(payload, dict):
            raise AnswerError("Qdrant hit is missing a payload object")
        hits.append({"score": float(item["score"]), "payload": payload})
    return hits


def retrieve(query: str, *, k: int = 5, min_score: float = DEFAULT_MIN_SCORE) -> list[dict]:
    """Return payload dicts whose similarity score clears min_score."""
    if k < 1:
        raise AnswerError("k must be at least 1")
    vector = embed(query)
    hits = _search(vector, k)
    return [hit["payload"] for hit in hits if hit["score"] >= min_score]


def _format_context(context: list[dict]) -> str:
    blocks: list[str] = []
    for item in context:
        try:
            document = item["source_document"]
            section = item["section"]
            text = item["text"]
        except KeyError as exc:
            raise AnswerError(f"Retrieved context is missing {exc.args[0]}") from exc
        blocks.append(f"[{document} / {section}]\n{text}")
    return "\n\n".join(blocks)


def _user_prompt(question: str, context: list[dict]) -> str:
    if not context:
        return (
            "No relevant context was retrieved.\n\n"
            f"Question: {question}\n\n"
            f"Reply with exactly this sentence and nothing else: {_NOT_ENOUGH}"
        )
    return (
        "Context:\n"
        "---\n"
        f"{_format_context(context)}\n"
        "---\n\n"
        f"Question: {question}"
    )


def _complete(user_prompt: str) -> str:
    _load_env()
    generation = _required("GENERATION_MODEL")
    embedding = _required("EMBEDDING_MODEL")
    if generation == embedding:
        raise AnswerError("GENERATION_MODEL and EMBEDDING_MODEL must be different models")
    base = os.getenv("GENERATION_BASE_URL", "").strip() or _required("EMBEDDING_BASE_URL")
    key = os.getenv("GENERATION_API_KEY", "").strip() or _required("EMBEDDING_API_KEY")
    request = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions",
        data=json.dumps(
            {
                "model": generation,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            }
        ).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:400]
        raise AnswerError(f"Generation request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise AnswerError(f"Generation endpoint is not reachable: {exc.reason}") from exc
    try:
        answer = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AnswerError("Generation response did not include choices[0].message.content") from exc
    if not isinstance(answer, str) or not answer.strip():
        raise AnswerError("Generation model returned an empty answer")
    return answer.strip()


def generate_answer(question: str, context: list[dict]) -> str:
    """Turn retrieved payloads into one English answer. Does not retrieve."""
    return _complete(_user_prompt(question, context))


def query(question: str) -> str:
    """Retrieve, then generate. Returns the answer string only."""
    return generate_answer(question, retrieve(question))


def main() -> None:
    questions = (
        "how many points do I need for Gold tier?",
        "does the BBQ Ribs dish have allergens?",
        "What is the wifi password for the Medellín office?",
    )
    for question in questions:
        vector = embed(question)
        hits = _search(vector, 5)
        scores = [hit["score"] for hit in hits]
        print(question)
        print(f"scores={scores}")
        print(query(question))
        print("---")


if __name__ == "__main__":
    main()
