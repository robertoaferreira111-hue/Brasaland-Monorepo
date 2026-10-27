"""Validate one event against docs/telemetry/event-schemas.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker
from jsonschema.exceptions import ValidationError

SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "telemetry" / "event-schemas.json"
)


class TelemetrySchemaError(ValueError):
    """The event is not in the approved catalog or fails its schema."""


@lru_cache(maxsize=1)
def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def approved_event_types() -> frozenset[str]:
    return frozenset(load_schema()["x-events"])


@lru_cache(maxsize=None)
def _validator(event_type: str) -> Draft7Validator:
    catalog = load_schema()
    document = {
        "$schema": catalog["$schema"],
        "definitions": catalog["definitions"],
        "x-events": catalog["x-events"],
        "$ref": f"#/x-events/{event_type}",
    }
    return Draft7Validator(document, format_checker=FormatChecker())


def _preferred_error(errors: list[ValidationError]) -> ValidationError:
    concrete = [
        error
        for error in errors
        if error.validator not in {"oneOf", "allOf", "anyOf"}
    ]
    return concrete[0] if concrete else errors[0]


def validate_event(event: dict) -> None:
    event_type = event.get("event_type")
    if not isinstance(event_type, str) or event_type not in approved_event_types():
        raise TelemetrySchemaError("event_type is not an approved event")
    errors = sorted(
        _validator(event_type).iter_errors(event),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if not errors:
        return
    error = _preferred_error(errors)
    location = ".".join(str(part) for part in error.absolute_path)
    prefix = f"{location}: " if location else ""
    raise TelemetrySchemaError(f"{prefix}{error.message}")
