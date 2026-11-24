"""State for one support question.

Each run answers the question it was given. The nodes need that question, the
context retrieved for it, the answer, any error, and the trace of this run.
Earlier turns are not stored. Carrying them would let a previous question
change retrieval and generation for the current one.
"""

from __future__ import annotations

import operator
from typing import Annotated, Sequence, TypedDict


class AgentState(TypedDict, total=False):
    question: str
    retrieved_context: list[dict] | None
    answer: str | None
    trace_steps: Annotated[Sequence[dict], operator.add]
    error: str | None
    route: str | None
    route_rationale: str | None
    incident_id: str | None
    incident_status: str | None
    incident_category: str | None
    incident_action: str | None
    incident_target_status: str | None
    tool_results: list[dict] | None
    tool_answer: str | None
    final_answer: str | None
