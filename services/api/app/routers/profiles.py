"""Profile updates for the signed-in user."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from tinydb.table import Table

from app.database import get_users_table, update_profile
from app.deps import current_user_email
from app.models import ProfileBody, ProfileResponse

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.put("/me", response_model=ProfileResponse)
def put_my_profile(
    payload: ProfileBody,
    email: Annotated[str, Depends(current_user_email)],
    users: Annotated[Table, Depends(get_users_table)],
) -> ProfileResponse:
    if not payload.name.strip() or not payload.phone.strip() or not payload.address.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name, phone, and address are required",
        )
    updated = update_profile(
        users,
        email,
        name=payload.name,
        phone=payload.phone,
        address=payload.address,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return updated
