"""POST /knowledge/query for the Brasaland manuals.

The route delegates to data.pipelines.rag.query. It does not retrieve,
embed, or call the generation model itself.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator

logger = logging.getLogger("brasaland.knowledge")

_UNAVAILABLE = "Knowledge service is unavailable"


def _repo_root() -> Path:
    configured = os.environ.get("BRASALAND_ROOT")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[4]


_REPO = _repo_root()
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from data.pipelines.rag import AnswerError, query  # noqa: E402
from data.process.rag import IndexingError  # noqa: E402

router = APIRouter(tags=["knowledge"])


class KnowledgeQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str

    @field_validator("question")
    @classmethod
    def question_must_have_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("question must not be empty")
        return text


class KnowledgeQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str


@router.post("/knowledge/query", response_model=KnowledgeQueryResponse)
def knowledge_query(body: KnowledgeQueryRequest) -> KnowledgeQueryResponse:
    try:
        answer = query(body.question)
    except (AnswerError, IndexingError):
        logger.exception("Knowledge query failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_UNAVAILABLE,
        ) from None
    return KnowledgeQueryResponse(answer=answer)
