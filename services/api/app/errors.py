"""Domain errors and safe client-facing messages for the supplier API."""

from __future__ import annotations

STORAGE_UNAVAILABLE = "Storage unavailable"
STORED_DATA_INVALID = "Stored supplier data is invalid"
UNEXPECTED_ERROR = "An unexpected error occurred"


class StorageError(Exception):
    """TinyDB or filesystem failure at the storage boundary."""


class DataIntegrityError(Exception):
    """A stored supplier document cannot be loaded into the domain model."""
