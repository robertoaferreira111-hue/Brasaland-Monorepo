"""Supplier HTTP routes backed by TinyDB."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.models import (
    Category,
    Country,
    RateUpdate,
    StatusUpdate,
    Supplier,
    SupplierCreate,
    SupplierResponse,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _response(supplier_id: int, document: dict) -> SupplierResponse:
    supplier = Supplier.from_storage(document)
    return SupplierResponse(id=supplier_id, **supplier.model_dump())


def _missing() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SupplierResponse)
def create_supplier(
    payload: SupplierCreate,
    table: Annotated[Table, Depends(get_table)],
) -> SupplierResponse:
    doc_id, document = persist_supplier(table, payload.model_dump())
    return _response(doc_id, document)


@router.get("", response_model=list[SupplierResponse])
def list_suppliers(
    table: Annotated[Table, Depends(get_table)],
    country: Annotated[Country | None, Query()] = None,
    category: Annotated[Category | None, Query()] = None,
) -> list[SupplierResponse]:
    rows = list_supplier_documents(table, country=country, category=category)
    return [_response(doc_id, document) for doc_id, document in rows]


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    table: Annotated[Table, Depends(get_table)],
) -> SupplierResponse:
    document = get_supplier_document(table, supplier_id)
    if document is None:
        raise _missing()
    return _response(supplier_id, document)


@router.patch("/{supplier_id}/rate", response_model=SupplierResponse)
def patch_rate(
    supplier_id: int,
    payload: RateUpdate,
    table: Annotated[Table, Depends(get_table)],
) -> SupplierResponse:
    document = update_supplier_rate(table, supplier_id, payload.rate_per_unit)
    if document is None:
        raise _missing()
    return _response(supplier_id, document)


@router.patch("/{supplier_id}/status", response_model=SupplierResponse)
def patch_status(
    supplier_id: int,
    payload: StatusUpdate,
    table: Annotated[Table, Depends(get_table)],
) -> SupplierResponse:
    document = update_supplier_status(table, supplier_id, payload.status)
    if document is None:
        raise _missing()
    return _response(supplier_id, document)


@router.delete("/{supplier_id}", response_model=SupplierResponse)
def remove_supplier(
    supplier_id: int,
    table: Annotated[Table, Depends(get_table)],
) -> SupplierResponse:
    document = delete_supplier(table, supplier_id)
    if document is None:
        raise _missing()
    return _response(supplier_id, document)
