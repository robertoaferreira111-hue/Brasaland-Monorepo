"""Make the services tree importable for the job_runner tests."""

from __future__ import annotations

import sys
from pathlib import Path

_SERVICES = Path(__file__).resolve().parents[2]
if str(_SERVICES) not in sys.path:
    sys.path.insert(0, str(_SERVICES))
