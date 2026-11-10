"""Import nightly_export.py for the script tests."""

from __future__ import annotations

import sys
from pathlib import Path

_SERVICES = Path(__file__).resolve().parents[2] / "services"
if str(_SERVICES) not in sys.path:
    sys.path.insert(0, str(_SERVICES))
