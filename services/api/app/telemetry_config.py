"""Telemetry endpoint setting.

Read once at import, the same way JWT_SECRET is read in app.security.
"""

import os
from urllib.parse import urlparse

DEFAULT_TELEMETRY_ENDPOINT = "http://localhost:8000/telemetry/events"


def path_from_endpoint(endpoint: str) -> str:
    """Return the URL path the FastAPI route should serve."""
    parsed = urlparse(endpoint.strip())
    path = parsed.path or "/telemetry/events"
    if not path.startswith("/"):
        path = f"/{path}"
    if len(path) > 1:
        path = path.rstrip("/")
    return path


TELEMETRY_ENDPOINT = os.getenv("TELEMETRY_ENDPOINT", DEFAULT_TELEMETRY_ENDPOINT)
TELEMETRY_PATH = path_from_endpoint(TELEMETRY_ENDPOINT)
