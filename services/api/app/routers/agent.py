"""POST /agent/query. Validate input, invoke the compiled graph, map errors.

This route does not retrieve, embed, or generate. Those steps stay in the graph.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator

logger = logging.getLogger("brasaland.agent")


def _repo_root() -> Path:
    configured = os.environ.get("BRASALAND_ROOT")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[4]


_REPO = _repo_root()
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from services.agent.graph import agent_graph  # noqa: E402
from services.agent.tracing import invoke_config, new_trace_id  # noqa: E402

router = APIRouter(tags=["agent"])

_EMPTY_QUESTION = "Question is empty."


class AgentQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str

    @field_validator("question")
    @classmethod
    def question_must_have_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("question must not be empty")
        return text


class AgentQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    trace_id: str


def _failure_detail(error: str, trace_id: str) -> tuple[int, str]:
    if error == _EMPTY_QUESTION:
        return status.HTTP_400_BAD_REQUEST, _EMPTY_QUESTION
    if error.startswith("Generation failed"):
        return (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Agent failed during generation. Check trace {trace_id}.",
        )
    if error.startswith("Retrieval failed"):
        return (
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Agent failed during retrieval. Check trace {trace_id}.",
        )
    return (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        f"Agent failed. Check trace {trace_id}.",
    )


@router.post("/agent/query", response_model=AgentQueryResponse)
def agent_query(body: AgentQueryRequest) -> AgentQueryResponse:
    trace_id = new_trace_id()
    try:
        result = agent_graph.invoke(
            {"question": body.question},
            invoke_config(trace_id),
        )
    except Exception:
        logger.exception("Agent query failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent failed. Check trace {trace_id}.",
        ) from None
    error = result.get("error")
    if error:
        code, detail = _failure_detail(str(error), trace_id)
        raise HTTPException(status_code=code, detail=detail) from None
    answer = result.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent failed. Check trace {trace_id}.",
        ) from None
    return AgentQueryResponse(answer=answer, trace_id=trace_id)
