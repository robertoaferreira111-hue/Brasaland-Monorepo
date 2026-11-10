"""Public job_runs operations.

Import this package without starting the FastAPI app. The functions live in
job_runner.py.
"""

from job_runner.job_runner import (
    create_run,
    has_completed_for_date,
    has_processing_lock,
    mark_completed,
    mark_failed,
    mark_processing,
)

__all__ = [
    "create_run",
    "has_completed_for_date",
    "has_processing_lock",
    "mark_completed",
    "mark_failed",
    "mark_processing",
]
