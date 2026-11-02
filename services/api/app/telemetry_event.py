"""TelemetryEvent validation against docs/telemetry/event-schemas.json.

The class did not exist in this service. Field rules come from that schema.
The schema file is not modified.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "telemetry"
    / "event-schemas.json"
)
_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_DATE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


class SchemaMismatch(Exception):
    """Instance failed the telemetry JSON Schema."""


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _expect_type(instance: object, type_name: str) -> None:
    if type_name == "string":
        ok = isinstance(instance, str)
    elif type_name == "object":
        ok = isinstance(instance, dict)
    elif type_name == "array":
        ok = isinstance(instance, list)
    elif type_name == "number":
        ok = _is_number(instance)
    elif type_name == "integer":
        ok = isinstance(instance, int) and not isinstance(instance, bool)
    elif type_name == "null":
        ok = instance is None
    else:
        ok = False
    if not ok:
        raise SchemaMismatch


def _expect_format(instance: object, fmt: str) -> None:
    if not isinstance(instance, str):
        raise SchemaMismatch
    if fmt == "uuid" and _UUID.fullmatch(instance) is None:
        raise SchemaMismatch
    if fmt == "date-time" and _DATE_TIME.fullmatch(instance) is None:
        raise SchemaMismatch
    if fmt not in {"uuid", "date-time"}:
        raise SchemaMismatch


def _resolve_ref(ref: str, root: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise SchemaMismatch
    node: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise SchemaMismatch
        node = node[part]
    if not isinstance(node, dict):
        raise SchemaMismatch
    return node


def _validate(instance: object, schema: dict[str, Any], root: dict[str, Any]) -> None:
    if "$ref" in schema:
        _validate(instance, _resolve_ref(schema["$ref"], root), root)
        return
    if "allOf" in schema:
        for sub in schema["allOf"]:
            _validate(instance, sub, root)
    if "anyOf" in schema:
        matched = False
        for sub in schema["anyOf"]:
            try:
                _validate(instance, sub, root)
            except SchemaMismatch:
                continue
            matched = True
            break
        if not matched:
            raise SchemaMismatch
    if "oneOf" in schema:
        matched = 0
        for sub in schema["oneOf"]:
            try:
                _validate(instance, sub, root)
            except SchemaMismatch:
                continue
            matched += 1
        if matched != 1:
            raise SchemaMismatch
    if "not" in schema:
        try:
            _validate(instance, schema["not"], root)
        except SchemaMismatch:
            pass
        else:
            raise SchemaMismatch
    if "const" in schema and instance != schema["const"]:
        raise SchemaMismatch
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaMismatch
    if "type" in schema:
        _expect_type(instance, schema["type"])
    if "minLength" in schema:
        if not isinstance(instance, str) or len(instance) < schema["minLength"]:
            raise SchemaMismatch
    if "maxLength" in schema:
        if not isinstance(instance, str) or len(instance) > schema["maxLength"]:
            raise SchemaMismatch
    if "pattern" in schema:
        if not isinstance(instance, str) or re.search(schema["pattern"], instance) is None:
            raise SchemaMismatch
    if "format" in schema:
        _expect_format(instance, schema["format"])
    if "minimum" in schema:
        if not _is_number(instance) or instance < schema["minimum"]:
            raise SchemaMismatch
    if "exclusiveMinimum" in schema:
        if not _is_number(instance) or instance <= schema["exclusiveMinimum"]:
            raise SchemaMismatch
    if "minItems" in schema:
        if not isinstance(instance, list) or len(instance) < schema["minItems"]:
            raise SchemaMismatch
    if "items" in schema:
        if not isinstance(instance, list):
            raise SchemaMismatch
        for item in instance:
            _validate(item, schema["items"], root)
    if schema.get("additionalProperties") is False and isinstance(instance, dict):
        allowed = set(schema.get("properties", {}))
        if any(key not in allowed for key in instance):
            raise SchemaMismatch
    if "properties" in schema and isinstance(instance, dict):
        for key, sub in schema["properties"].items():
            if key in instance:
                _validate(instance[key], sub, root)
    if "required" in schema:
        if not isinstance(instance, dict) or any(
            key not in instance for key in schema["required"]
        ):
            raise SchemaMismatch


@lru_cache(maxsize=1)
def load_telemetry_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def event_matches_schema(instance: dict[str, Any]) -> None:
    schema = load_telemetry_schema()
    _validate(instance, schema, schema)


class TelemetryEvent(BaseModel):
    """One event. `model_validate` accepts a raw dict and enforces the schema."""

    model_config = ConfigDict(extra="forbid")

    eventId: str
    timestamp: str
    sessionId: str | None
    userId: str | None
    event_type: str
    entity_action: str
    schemaVersion: str
    requestId: str
    properties: dict[str, Any]

    @model_validator(mode="after")
    def enforce_contract(self) -> TelemetryEvent:
        try:
            event_matches_schema(self.model_dump(mode="python"))
        except SchemaMismatch as exc:
            raise ValueError("event does not match the telemetry contract") from exc
        return self
