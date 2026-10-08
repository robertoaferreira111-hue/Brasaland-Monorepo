"""Request and response models for staff auth."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


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
