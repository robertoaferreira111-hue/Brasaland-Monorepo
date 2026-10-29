"""Simple in-process rate limiting for password-reset requests."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

# Per-email window for forgot-password sends.
FORGOT_WINDOW_SECONDS = 15 * 60
FORGOT_MAX_ATTEMPTS = 5

_lock = Lock()
_forgot_hits: dict[str, list[float]] = defaultdict(list)


def allow_forgot_password(email: str) -> bool:
    """Return True when another reset email may be sent for this address."""
    key = email.strip().lower()
    now = time.time()
    with _lock:
        recent = [stamp for stamp in _forgot_hits[key] if now - stamp < FORGOT_WINDOW_SECONDS]
        if len(recent) >= FORGOT_MAX_ATTEMPTS:
            _forgot_hits[key] = recent
            return False
        recent.append(now)
        _forgot_hits[key] = recent
        return True


def reset_forgot_password_limits() -> None:
    """Test helper to clear in-memory counters."""
    with _lock:
        _forgot_hits.clear()
