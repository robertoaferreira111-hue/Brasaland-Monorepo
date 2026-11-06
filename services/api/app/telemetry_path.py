"""Ensure `services/telemetry` modules are importable from the API process."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_telemetry_on_path() -> Path:
    candidates: list[Path] = []
    root = os.environ.get("BRASALAND_ROOT")
    if root:
        candidates.append(Path(root) / "services" / "telemetry")
    here = Path(__file__).resolve()
    candidates.append(here.parents[2] / "telemetry")
    candidates.append(Path("/opt/brasaland/services/telemetry"))
    for path in candidates:
        if (path / "router.py").is_file():
            root_s = str(path)
            if root_s not in sys.path:
                sys.path.insert(0, root_s)
            return path
    raise RuntimeError("services/telemetry is missing")
