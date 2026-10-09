"""Environment-backed settings for auth and email."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_env_files() -> None:
    """Load secrets without overriding already-exported process env vars."""
    candidates = (
        REPO_ROOT / ".env" / "local",
        REPO_ROOT / ".env",
        API_ROOT / ".env",
    )
    for path in candidates:
        if path.is_file():
            load_dotenv(path, override=False)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    reset_token_expire_minutes: int
    frontend_url: str
    resend_api_key: str | None
    sendgrid_api_key: str | None
    email_from: str
    min_password_length: int = 8

    @property
    def email_provider(self) -> str | None:
        if self.resend_api_key:
            return "resend"
        if self.sendgrid_api_key:
            return "sendgrid"
        return None


@lru_cache
def get_settings() -> Settings:
    _load_env_files()
    reset_minutes = _int_env("RESET_TOKEN_EXPIRE_MINUTES", 30)
    if reset_minutes < 15 or reset_minutes > 60:
        raise ValueError(
            "RESET_TOKEN_EXPIRE_MINUTES must be between 15 and 60 (assignment window)"
        )
    return Settings(
        jwt_secret=os.getenv("JWT_SECRET", "dev-only-change-me"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=_int_env("ACCESS_TOKEN_EXPIRE_MINUTES", 60),
        reset_token_expire_minutes=reset_minutes,
        frontend_url=os.getenv("FRONTEND_URL", "http://localhost:3001").rstrip("/"),
        resend_api_key=os.getenv("RESEND_API_KEY") or None,
        sendgrid_api_key=os.getenv("SENDGRID_API_KEY") or None,
        email_from=os.getenv("EMAIL_FROM", "Brasaland <onboarding@resend.dev>"),
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()
