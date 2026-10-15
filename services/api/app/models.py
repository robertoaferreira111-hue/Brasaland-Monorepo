"""Supplier schema from the Brasaland supplier-directory context."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

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
