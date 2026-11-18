"""Choose RAG, the ticket tool, or both without a model call.

An incident id is ``BRS-`` plus six digits, or a bare number written next to
the word incident or ticket (``incident 12`` becomes ``BRS-000012``). A
status or category filter is used only when the question asks for incidents
and does not already name an id. Naming an id wins, so "what is the status
of BRS-000012?" looks up that row instead of treating the word status as a
filter.

When more than one id appears, only the first is looked up. A question that
says incident without an id, a filter, or a list request stays on the
manuals. ``both`` looks up the ticket first and then the manuals, so the
incident fields come from the service.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from services.agent.tools.ticket_lookup import normalize_incident_id

RouteName = Literal["rag", "tool", "both"]

_BRS = re.compile(r"\bBRS-\d{1,6}\b", re.IGNORECASE)
_LABELED_NUMBER = re.compile(
    r"\b(?:incident|ticket)\s*#?\s*(\d{1,6})\b",
    re.IGNORECASE,
)
_INCIDENT_WORD = re.compile(r"\b(?:incidents?|tickets?)\b", re.IGNORECASE)
_LIST_REQUEST = re.compile(r"\b(?:list|show|which|all)\b", re.IGNORECASE)
_POLICY = re.compile(
    r"\b(?:policy|procedure|procedures|refund|recipe|recipes|loyalty|"
    r"manual|manuals|training|waste|onboarding|points)\b|"
    r"\bshould we\b|\bwhat should\b",
    re.IGNORECASE,
)
_STATUS_WORDS = (
    ("open", "OPEN"),
    ("closed", "CLOSED"),
    ("discarded", "DISCARDED"),
)
_CATEGORY_PHRASES = (
    ("customer complaint", "CUSTOMER_COMPLAINT"),
    ("food quality", "FOOD_QUALITY"),
    ("equipment", "EQUIPMENT"),
    ("supply", "SUPPLY"),
    ("staff", "STAFF"),
)


@dataclass(frozen=True)
class RouteDecision:
    route: RouteName
    incident_id: str | None
    status: str | None
    category: str | None
    rationale: str


def decide_route(question: str) -> RouteDecision:
    """Return the same decision for the same question every time."""
    text = question.strip()
    ids = _ids(text)
    incident_id = ids[0] if ids else None
    mentions_incident = _INCIDENT_WORD.search(text) is not None
    statuses = _statuses(text) if incident_id is None and mentions_incident else []
    categories = _categories(text) if incident_id is None and mentions_incident else []
    status = statuses[0] if len(statuses) == 1 else None
    category = categories[0] if len(categories) == 1 else None
    listed = mentions_incident and _LIST_REQUEST.search(text) is not None
    filtered = bool(status or category or len(statuses) > 1 or len(categories) > 1)
    wants_tool = incident_id is not None or listed or filtered
    policy = _POLICY.search(text) is not None
    if wants_tool and policy:
        route: RouteName = "both"
    elif wants_tool:
        route = "tool"
    else:
        route = "rag"
    return RouteDecision(
        route=route,
        incident_id=incident_id,
        status=status,
        category=category,
        rationale=_rationale(
            route=route,
            incident_id=incident_id,
            extra_ids=ids[1:],
            status=status,
            category=category,
            statuses=statuses,
            categories=categories,
            mentions_incident=mentions_incident,
            wants_tool=wants_tool,
        ),
    )


def _ids(text: str) -> list[str]:
    found: list[str] = []
    for match in _BRS.finditer(text):
        _add(found, match.group(0))
    if found:
        return found
    for match in _LABELED_NUMBER.finditer(text):
        _add(found, match.group(1))
    return found


def _add(found: list[str], raw: str) -> None:
    normalized = normalize_incident_id(raw)
    if normalized is not None and normalized not in found:
        found.append(normalized)


def _statuses(text: str) -> list[str]:
    found: list[str] = []
    for word, value in _STATUS_WORDS:
        if re.search(rf"\b{word}\b", text, re.IGNORECASE) and value not in found:
            found.append(value)
    return found


def _categories(text: str) -> list[str]:
    lowered = text.casefold()
    found: list[str] = []
    for phrase, value in _CATEGORY_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", lowered) and value not in found:
            found.append(value)
    return found


def _rationale(
    *,
    route: RouteName,
    incident_id: str | None,
    extra_ids: list[str],
    status: str | None,
    category: str | None,
    statuses: list[str],
    categories: list[str],
    mentions_incident: bool,
    wants_tool: bool,
) -> str:
    if route == "rag" and mentions_incident and not wants_tool:
        return (
            "The question mentions an incident but not an id, a status, a "
            "category, or a list request, so no ticket lookup is run."
        )
    if route == "rag":
        return "No incident id and no incident filter. Answer from the manuals."
    parts: list[str] = []
    if incident_id is not None:
        parts.append(f"Look up incident {incident_id}.")
        if extra_ids:
            skipped = ", ".join(extra_ids)
            parts.append(f"Other ids are not looked up: {skipped}.")
        parts.append("An id is not combined with a status or category filter.")
    else:
        filters: list[str] = []
        if status is not None:
            filters.append(f"status {status}")
        if category is not None:
            filters.append(f"category {category}")
        if len(statuses) > 1:
            parts.append("More than one status was named, so status is not filtered.")
        if len(categories) > 1:
            parts.append(
                "More than one category was named, so category is not filtered."
            )
        if filters:
            parts.append("Look up incidents with " + " and ".join(filters) + ".")
        elif not parts:
            parts.append("Look up incidents with no status or category filter.")
    if route == "both":
        parts.append(
            "The question also asks about procedure. Order: ticket tool, then manuals."
        )
    else:
        parts.append("Do not consult the manuals.")
    return " ".join(parts)
