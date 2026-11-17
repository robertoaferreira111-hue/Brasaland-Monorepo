"""Index the four Brasaland manuals in Qdrant.

setup() chunks those manuals and upserts them. embed() is the only embedding
call, shared by indexing now and by later queries. This module does not
retrieve, generate, or expose an HTTP route.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

COLLECTION = "brasaland_knowledge"
COMPANY = "brasaland"
LANGUAGE = "en"
_ID_NAMESPACE = uuid.UUID("6f0d5a1e-4c2b-5d7e-8a91-0b3c4d5e6f70")

SOURCE_DOCUMENTS = {
    "brasaland-loyalty-program.en.md": "loyalty-program",
    "brasaland-waste-protocol.en.md": "waste-protocol",
    "brasaland-menu-allergens.en.md": "menu-allergens",
    "brasaland-supplier-ordering.en.md": "supplier-ordering",
}

# Phrases that must survive as one contiguous excerpt. A split would drop the
# amount, threshold, or allergen sentence out of every chunk.
_INTACT = {
    "loyalty-program": (
        "10,000 COP (or 10 USD",
        "20,000 COP (20 USD)",
        "Bronze (0-19 points): 5% off drinks on Tuesdays.",
        "Silver (20-49 points): 10% off the main dish, once a month.",
        "Gold (50+ points): 15% permanent discount",
        "at the day's exchange rate",
    ),
    "waste-protocol": (
        "Any waste over 2 kg of meat protein",
        "Unexplained shrinkage above 3% of an ingredient's weekly inventory",
        "exceeding 5 kg in a week",
        "keep total waste below 4% of monthly ingredient cost",
        "Locations exceeding 6% for two consecutive months",
    ),
    "menu-allergens": (
        "contains soy.",
        "may contain trace peanuts",
        '"Zero cross-contamination risk" is never guaranteed',
        "There is no certified gluten-free version of the BBQ Ribs",
    ),
    "supplier-ordering": (
        "less than 3 days of",
        "8% surcharge over list price",
        "500 USD (or the COP equivalent)",
    ),
}


class IndexingError(RuntimeError):
    """The manuals cannot be indexed as the briefing requires."""


@dataclass(frozen=True)
class Chunk:
    source_document: str
    section: str
    chunk_index: int
    text: str

    def point_id(self) -> str:
        name = f"{COMPANY}|{self.source_document}|{self.section}|{self.chunk_index}"
        return str(uuid.uuid5(_ID_NAMESPACE, name))

    def payload(self) -> dict[str, Any]:
        return {
            "company": COMPANY,
            "source_document": self.source_document,
            "section": self.section,
            "language": LANGUAGE,
            "chunk_index": self.chunk_index,
            "text": self.text,
        }


def _repo_root() -> Path:
    configured = os.environ.get("BRASALAND_ROOT")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2]


def _load_env() -> None:
    """Load the repo env files without overriding variables already set."""
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise IndexingError(
            "python-dotenv is not installed. Run this with: "
            "uv run --project services/api python data/process/rag.py"
        ) from exc
    root = _repo_root()
    for path in (root / ".env" / "local", root / ".env", root / "services" / "api" / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise IndexingError(f"{name} is not set. Add it to .env before running setup().")
    return value


def _section_name(block: str, title: str, block_index: int) -> str:
    first = block.splitlines()[0].strip()
    if first.endswith(":"):
        return first[:-1].strip()
    if ":" in first:
        label = first.split(":", 1)[0].strip()
        if label and len(label.split()) <= 12:
            return label
    if block_index == 0:
        return title
    sentence = " ".join(block.split()).split(". ", 1)[0]
    return sentence.rstrip(".")


def _chunk_document(raw: str, source_document: str) -> list[Chunk]:
    """Split one manual on blank-line boundaries.

    Headings, tier lists, dish lists, and numbered procedures are single
    blocks in these files, so a blank-line split keeps each of them whole.
    """
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise IndexingError(f"{source_document} is missing its title heading")
    title = lines[0][2:].strip()
    body = "\n".join(lines[1:]).strip("\n")
    blocks = [block.strip("\n") for block in body.split("\n\n") if block.strip()]
    if len(blocks) < 3:
        raise IndexingError(f"{source_document} produced fewer than 3 chunks")

    counts: dict[str, int] = {}
    chunks: list[Chunk] = []
    for block_index, block in enumerate(blocks):
        chunk_text = f"{lines[0]}\n\n{block}" if block_index == 0 else block
        if "\n" not in chunk_text:
            raise IndexingError(f"{source_document} produced a single-line chunk")
        if chunk_text.strip() == text.strip():
            raise IndexingError(f"{source_document} was indexed as one chunk")
        if chunk_text not in text:
            raise IndexingError(f"{source_document} chunk is not an exact excerpt")
        section = _section_name(block, title, block_index)
        chunk_index = counts.get(section, 0)
        counts[section] = chunk_index + 1
        chunks.append(
            Chunk(
                source_document=source_document,
                section=section,
                chunk_index=chunk_index,
                text=chunk_text,
            )
        )
    return chunks


def _compact(value: str) -> str:
    return " ".join(value.split())


def _assert_intact(chunks: list[Chunk]) -> None:
    for source_document, phrases in _INTACT.items():
        own = [chunk.text for chunk in chunks if chunk.source_document == source_document]
        for phrase in phrases:
            hits = sum(_compact(phrase) in _compact(text) for text in own)
            if hits != 1:
                raise IndexingError(
                    f"{source_document} phrase {phrase!r} appears in {hits} chunks"
                )


def load_chunks() -> list[Chunk]:
    """Read only the four briefing manuals and chunk each one."""
    folder = _repo_root() / "docs" / "company-knowledge-base"
    chunks: list[Chunk] = []
    for filename, source_document in SOURCE_DOCUMENTS.items():
        path = folder / filename
        if not path.is_file():
            raise IndexingError(f"Missing knowledge-base file: {path}")
        chunks.extend(_chunk_document(path.read_text(encoding="utf-8"), source_document))
    _assert_intact(chunks)
    return chunks


def _qdrant_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        if exc.code == 404:
            return {"status": 404, "body": body}
        raise IndexingError(f"Qdrant {method} {url} returned {exc.code}: {body[:400]}") from exc
    except urllib.error.URLError as exc:
        raise IndexingError(f"Qdrant is not reachable at {url}: {exc.reason}") from exc
    return json.loads(raw) if raw else {}


def _vector_size(collection: dict[str, Any]) -> int | None:
    if collection.get("status") == 404:
        return None
    vectors = collection.get("result", {}).get("config", {}).get("params", {}).get("vectors")
    if isinstance(vectors, dict) and "size" in vectors:
        return int(vectors["size"])
    if isinstance(vectors, dict):
        for value in vectors.values():
            if isinstance(value, dict) and "size" in value:
                return int(value["size"])
    raise IndexingError("Qdrant collection exists but its vector size could not be read")


def _count(base: str, source_document: str | None = None) -> int:
    body: dict[str, Any] = {"exact": True}
    if source_document is not None:
        body["filter"] = {
            "must": [{"key": "source_document", "match": {"value": source_document}}]
        }
    counted = _qdrant_json(
        "POST",
        f"{base}/collections/{COLLECTION}/points/count",
        body,
    )
    return int(counted.get("result", {}).get("count", 0))


def embed(text: str) -> list[float]:
    """Embed one string with the 4Geeks embedding model."""
    if not text.strip():
        raise IndexingError("embed() received an empty string")
    _load_env()
    model = _required("EMBEDDING_MODEL")
    generation = _required("GENERATION_MODEL")
    if model == generation:
        raise IndexingError("EMBEDDING_MODEL and GENERATION_MODEL must be different models")
    base = _required("EMBEDDING_BASE_URL").rstrip("/")
    key = _required("EMBEDDING_API_KEY")
    request = urllib.request.Request(
        f"{base}/embeddings",
        data=json.dumps({"model": model, "input": text}).encode(),
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
        raise IndexingError(f"Embedding request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise IndexingError(f"Embedding endpoint is not reachable: {exc.reason}") from exc
    try:
        vector = payload["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as exc:
        raise IndexingError("Embedding response did not include data[0].embedding") from exc
    values = [float(item) for item in vector]
    configured = os.getenv("EMBEDDING_DIMENSION", "").strip()
    if configured and len(values) != int(configured):
        raise IndexingError(
            f"Embedding length {len(values)} does not match EMBEDDING_DIMENSION={configured}"
        )
    return values


def setup() -> dict[str, Any]:
    """Chunk the four manuals and upsert them into brasaland_knowledge."""
    chunks = load_chunks()
    _load_env()
    base = os.getenv("QDRANT_URL", "http://127.0.0.1:6333").strip().rstrip("/")
    vectors = [embed(chunk.text) for chunk in chunks]
    dimension = len(vectors[0])
    if any(len(vector) != dimension for vector in vectors):
        raise IndexingError("embed() returned vectors of different lengths")

    existing = _qdrant_json("GET", f"{base}/collections/{COLLECTION}")
    existing_size = _vector_size(existing)
    if existing_size is None:
        _qdrant_json(
            "PUT",
            f"{base}/collections/{COLLECTION}",
            {"vectors": {"size": dimension, "distance": "Cosine"}},
        )
    elif existing_size != dimension:
        raise IndexingError(
            f"Collection {COLLECTION} has dimension {existing_size}, embeddings have {dimension}"
        )

    before = _count(base) if existing_size is not None else 0
    points = [
        {"id": chunk.point_id(), "vector": vector, "payload": chunk.payload()}
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    _qdrant_json(
        "PUT",
        f"{base}/collections/{COLLECTION}/points?wait=true",
        {"points": points},
    )
    stored = _qdrant_json("GET", f"{base}/collections/{COLLECTION}/points/{points[0]['id']}")
    payload = stored.get("result", {}).get("payload", {})
    expected = chunks[0].payload()
    if payload != expected:
        raise IndexingError("Stored payload does not match the briefing fields")

    per_document = {
        source_document: _count(base, source_document)
        for source_document in SOURCE_DOCUMENTS.values()
    }
    return {
        "collection": COLLECTION,
        "dimension": dimension,
        "embedding_model": os.environ["EMBEDDING_MODEL"].strip(),
        "generation_model": os.environ["GENERATION_MODEL"].strip(),
        "chunks_per_document": {
            source_document: sum(chunk.source_document == source_document for chunk in chunks)
            for source_document in SOURCE_DOCUMENTS.values()
        },
        "points_before": before,
        "points_after": _count(base),
        "stored_per_document": per_document,
    }


def main() -> None:
    first = setup()
    second = setup()
    report = {
        "collection": first["collection"],
        "dimension": first["dimension"],
        "embedding_model": first["embedding_model"],
        "generation_model": first["generation_model"],
        "chunks_per_document": first["chunks_per_document"],
        "first_run": {
            "points_before": first["points_before"],
            "points_after": first["points_after"],
        },
        "second_run": {
            "points_before": second["points_before"],
            "points_after": second["points_after"],
        },
        "stored_per_document": second["stored_per_document"],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
