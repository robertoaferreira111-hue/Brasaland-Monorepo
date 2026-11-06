"""Direct Postgres access for the business performance pipeline.

The pipeline reads and writes the database only through this module.
``DATABASE_URL`` comes from the API settings object.
"""

from __future__ import annotations

from typing import Any

import psycopg


def connect() -> Any:
    """Open one connection. Caller closes it."""
    from app.config import get_settings

    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(url)
