"""Ensure `services/telemetry` modules are importable from the API process."""

from __future__ import annotations

import sys
from pathlib import Path

_TELEMETRY_ROOT = Path(__file__).resolve().parents[2] / "telemetry"


def ensure_telemetry_on_path() -> Path:
    root = str(_TELEMETRY_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return _TELEMETRY_ROOT
