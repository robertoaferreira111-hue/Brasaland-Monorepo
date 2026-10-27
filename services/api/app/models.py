"""Supplier schema and staff auth models."""

import re
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

VALID_CATEGORIES = (
    "carne",
    "verduras_y_hortalizas",
    "salsas_y_condimentos",
    "bebidas",
    "packaging",
    "productos_limpieza",
    "lacteos",
    "carbon_y_combustible",
)

VALID_STATUSES = ("active", "suspended")

CURRENCY_BY_COUNTRY = {
    "Colombia": "COP",
    "USA": "USD",
}

Category = Literal[
    "carne",
    "verduras_y_hortalizas",
    "salsas_y_condimentos",
    "bebidas",
    "packaging",
    "productos_limpieza",
    "lacteos",
    "carbon_y_combustible",
]

Status = Literal["active", "suspended"]
Country = Literal["Colombia", "USA"]
Currency = Literal["COP", "USD"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_positive_rate(value: float) -> float:
    if value <= 0:
        raise ValueError("rate_per_unit must be greater than 0")
    return value


def ensure_currency_matches_country(country: str, currency: str) -> None:
    expected = CURRENCY_BY_COUNTRY[country]
    if currency != expected:
        raise ValueError(
            f'currency must be "{expected}" when country is "{country}"'
        )


class Supplier(BaseModel):
    """One Brasaland supplier. `updated_at` is set by the system on create."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    country: Country
    categories: list[Category] = Field(min_length=1)
    rate_per_unit: float
    currency: Currency
    updated_at: datetime = Field(default_factory=_utcnow)
    status: Status
    contact_email: str | None = None
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def discard_client_timestamp(cls, data: object, info: ValidationInfo) -> object:
        if not isinstance(data, dict):
            return data
        if info.context and info.context.get("source") == "client":
            payload = dict(data)
            payload.pop("updated_at", None)
            return payload
        return data

    @field_validator("rate_per_unit")
    @classmethod
    def rate_must_be_positive(cls, value: float) -> float:
        return ensure_positive_rate(value)

    @model_validator(mode="after")
    def currency_matches_country(self) -> "Supplier":
        ensure_currency_matches_country(self.country, self.currency)
        return self

    @classmethod
    def from_client(cls, data: dict) -> "Supplier":
        """Build a new supplier. Any client `updated_at` is ignored."""
        return cls.model_validate(data, context={"source": "client"})

    @classmethod
    def from_storage(cls, data: dict) -> "Supplier":
        """Load a supplier already stored in TinyDB, keeping its timestamp."""
        return cls.model_validate(data)


class SupplierCreate(BaseModel):
    """Client payload for a new supplier. `updated_at` and `id` are not accepted."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    country: Country
    categories: list[Category] = Field(min_length=1)
    rate_per_unit: float
    currency: Currency
    status: Status
    contact_email: str | None = None
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_system_fields(cls, data: object) -> object:
        if isinstance(data, dict) and ("updated_at" in data or "id" in data):
            raise ValueError("updated_at and id are assigned by the system")
        return data

    @field_validator("rate_per_unit")
    @classmethod
    def rate_must_be_positive(cls, value: float) -> float:
        return ensure_positive_rate(value)

    @model_validator(mode="after")
    def currency_matches_country(self) -> "SupplierCreate":
        ensure_currency_matches_country(self.country, self.currency)
        return self


class RateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rate_per_unit: float

    @field_validator("rate_per_unit")
    @classmethod
    def rate_must_be_positive(cls, value: float) -> float:
        return ensure_positive_rate(value)


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status


class SupplierResponse(Supplier):
    """Stored supplier plus the TinyDB document id used by the API routes."""

    id: int


class RegisterUser(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3)
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip()
        if not EMAIL_PATTERN.match(email):
            raise ValueError("Enter a valid email (example: name@email.com)")
        return email.lower()


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)


class ProfileBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    phone: str
    address: str


class ProfileResponse(BaseModel):
    email: str
    name: str = ""
    phone: str = ""
    address: str = ""


UUID_PATTERN = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}"
    r"-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
EVENT_NAME_PATTERN = r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$"


class TelemetryEvent(BaseModel):
    """Approved telemetry envelope from docs/telemetry/event-schemas.json."""

    model_config = ConfigDict(extra="forbid")

    eventId: str = Field(pattern=UUID_PATTERN)
    timestamp: str = Field(min_length=1)
    sessionId: str = Field(pattern=UUID_PATTERN)
    userId: str | None
    event_type: str = Field(pattern=EVENT_NAME_PATTERN)
    entity_action: str = Field(pattern=EVENT_NAME_PATTERN)
    schemaVersion: Literal["1.0.0"]
    requestId: str = Field(pattern=UUID_PATTERN)
    properties: dict[str, Any]

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_utc(cls, value: str) -> str:
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("timestamp must be an ISO 8601 UTC date-time") from exc
        if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
            raise ValueError("timestamp must be UTC")
        return value

    @field_validator("userId")
    @classmethod
    def user_id_is_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("userId must be null or a non-empty opaque id")
        return value

    @model_validator(mode="after")
    def entity_action_matches_event_type(self) -> "TelemetryEvent":
        if self.entity_action != self.event_type:
            raise ValueError("entity_action must equal event_type")
        return self


class TelemetryBatch(BaseModel):
    """Batch posted to the telemetry stub. An empty list is invalid."""

    model_config = ConfigDict(extra="forbid")

    events: list[TelemetryEvent] = Field(min_length=1)


class TelemetryBatchResponse(BaseModel):
    """Acknowledgement. The stub counts the batch and stores nothing."""

    received: int = Field(ge=1)
