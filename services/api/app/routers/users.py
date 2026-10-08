"""User registration."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from tinydb.table import Table

from app.database import create_user, get_users_table
from app.models import ProfileResponse, RegisterUser

router = APIRouter(tags=["users"])


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=ProfileResponse)
def register_user(
    payload: RegisterUser,
    table: Annotated[Table, Depends(get_users_table)],
) -> ProfileResponse:
    try:
        return create_user(table, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
