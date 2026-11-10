"""Celery tasks discovered from the Brasaland API worker."""

from app.tasks.weekly_pipeline import run_weekly_pipeline

__all__ = ["run_weekly_pipeline"]
