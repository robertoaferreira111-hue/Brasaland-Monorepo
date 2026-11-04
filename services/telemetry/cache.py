"""Process-local TTL cache for telemetry report payloads."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Callable


class ReportCache:
    """In-memory cache keyed by normalized (start, end) ISO strings."""

    def __init__(
        self,
        *,
        ttl_seconds: float = 60.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._ttl = float(ttl_seconds)
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._store: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}

    @staticmethod
    def make_key(start: datetime, end: datetime) -> tuple[str, str]:
        return (start.isoformat(), end.isoformat())

    def get(self, start: datetime, end: datetime) -> dict[str, Any] | None:
        key = self.make_key(start, end)
        now = self._clock()
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, payload = item
            if now >= expires_at:
                del self._store[key]
                return None
            return payload

    def set(self, start: datetime, end: datetime, payload: dict[str, Any]) -> None:
        key = self.make_key(start, end)
        expires_at = self._clock() + self._ttl
        with self._lock:
            self._store[key] = (expires_at, payload)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
