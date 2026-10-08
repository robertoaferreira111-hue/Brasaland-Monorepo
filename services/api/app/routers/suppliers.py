"""Supplier HTTP routes backed by TinyDB."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from tinydb.table import Table

from app.database import (
    delete_supplier,
    get_supplier_document,
    get_table,
    list_supplier_documents,
    persist_supplier,
    update_supplier_rate,
    update_supplier_status,
)
from app.errors import (
    STORAGE_UNAVAILABLE,
    STORED_DATA_INVALID,
    DataIntegrityError,
    StorageError,
)
from app.models import (
    Category,
    Country,
    RateUpdate,
    StatusUpdate,
    Supplier,
    SupplierCreate,
    SupplierResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _missing() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found"
    )


def _storage_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=STORAGE_UNAVAILABLE,
    )


def _stored_data_invalid() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=STORED_DATA_INVALID,
    )


def get_suppliers_table() -> Iterator[Table]:
    """Dependency wrapper that maps storage failures to a safe HTTP 500."""
    try:
        yield from get_table()
    except StorageError as exc:
        raise _storage_unavailable() from exc


def _response(supplier_id: int, document: dict) -> SupplierResponse:
    try:
        supplier = Supplier.from_storage(document)
    except ValidationError as exc:
        logger.warning(
            "Corrupt supplier document id=%s cannot be loaded: %s",
            supplier_id,
            exc.error_count(),
        )
        raise DataIntegrityError(STORED_DATA_INVALID) from exc
    return SupplierResponse(id=supplier_id, **supplier.model_dump())


def _require_response(supplier_id: int, document: dict) -> SupplierResponse:
    try:
        return _response(supplier_id, document)
    except DataIntegrityError as exc:
        raise _stored_data_invalid() from exc


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SupplierResponse)
def create_supplier(
    payload: SupplierCreate,
    table: Annotated[Table, Depends(get_suppliers_table)],
) -> SupplierResponse:
    try:
        doc_id, document = persist_supplier(table, payload.model_dump())
        return _require_response(doc_id, document)
    except StorageError as exc:
        raise _storage_unavailable() from exc


@router.get("", response_model=list[SupplierResponse])
def list_suppliers(
    table: Annotated[Table, Depends(get_suppliers_table)],
    country: Annotated[Country | None, Query()] = None,
    category: Annotated[Category | None, Query()] = None,
) -> list[SupplierResponse]:
    try:
        rows = list_supplier_documents(table, country=country, category=category)
    except StorageError as exc:
        raise _storage_unavailable() from exc

    results: list[SupplierResponse] = []
    for doc_id, document in rows:
        try:
            results.append(_response(doc_id, document))
        except DataIntegrityError:
            logger.warning("Skipping corrupt supplier document id=%s", doc_id)
            continue
    return results


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    table: Annotated[Table, Depends(get_suppliers_table)],
) -> SupplierResponse:
    try:
        document = get_supplier_document(table, supplier_id)
    except StorageError as exc:
        raise _storage_unavailable() from exc
    if document is None:
        raise _missing()
    return _require_response(supplier_id, document)


@router.patch("/{supplier_id}/rate", response_model=SupplierResponse)
def patch_rate(
    supplier_id: int,
    payload: RateUpdate,
    table: Annotated[Table, Depends(get_suppliers_table)],
) -> SupplierResponse:
    try:
        document = update_supplier_rate(table, supplier_id, payload.rate_per_unit)
    except StorageError as exc:
        raise _storage_unavailable() from exc
    except ValidationError as exc:
        logger.warning("Cannot update rate for corrupt supplier id=%s", supplier_id)
        raise _stored_data_invalid() from exc
    if document is None:
        raise _missing()
    return _require_response(supplier_id, document)


@router.patch("/{supplier_id}/status", response_model=SupplierResponse)
def patch_status(
    supplier_id: int,
    payload: StatusUpdate,
    table: Annotated[Table, Depends(get_suppliers_table)],
) -> SupplierResponse:
    try:
        document = update_supplier_status(table, supplier_id, payload.status)
    except StorageError as exc:
        raise _storage_unavailable() from exc
    except ValidationError as exc:
        logger.warning("Cannot update status for corrupt supplier id=%s", supplier_id)
        raise _stored_data_invalid() from exc
    if document is None:
        raise _missing()
    return _require_response(supplier_id, document)


@router.delete("/{supplier_id}", response_model=SupplierResponse)
def remove_supplier(
    supplier_id: int,
    table: Annotated[Table, Depends(get_suppliers_table)],
) -> SupplierResponse:
    try:
        document = get_supplier_document(table, supplier_id)
    except StorageError as exc:
        raise _storage_unavailable() from exc
    if document is None:
        raise _missing()
    response = _require_response(supplier_id, document)
    try:
        deleted = delete_supplier(table, supplier_id)
    except StorageError as exc:
        raise _storage_unavailable() from exc
    if deleted is None:
        raise _missing()
    return response
