"""Stable public error-detail strings consumed by the backoffice UI."""

from app.errors import (
    STORAGE_UNAVAILABLE,
    STORED_DATA_INVALID,
    UNEXPECTED_ERROR,
)


def test_public_error_detail_strings_remain_stable_for_frontend_contract():
    # Mirrored in uis/backoffice/supplierErrors.mjs → BACKEND_SAFE_DETAILS
    assert STORAGE_UNAVAILABLE == "Storage unavailable"
    assert STORED_DATA_INVALID == "Stored supplier data is invalid"
    assert UNEXPECTED_ERROR == "An unexpected error occurred"
