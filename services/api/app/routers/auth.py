"""Login, logout, refresh, and current user."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from tinydb.table import Table

from app.database import (
    authenticate_user,
    find_user,
    get_refresh_table,
    get_users_table,
    profile_from_user,
    refresh_token_active,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    store_refresh_token,
)
from app.deps import current_user_email
from app.models import LoginBody, ProfileResponse, RefreshBody, TokenResponse
from app.security import create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(
    email: str,
    refresh_table: Table,
) -> TokenResponse:
    access_token = create_access_token(email)
    refresh_token, jti = create_refresh_token(email)
    store_refresh_token(refresh_table, jti, email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginBody,
    users: Annotated[Table, Depends(get_users_table)],
    refresh_tokens: Annotated[Table, Depends(get_refresh_table)],
) -> TokenResponse:
    user = authenticate_user(users, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return _issue_tokens(user["email"], refresh_tokens)


@router.get("/me", response_model=ProfileResponse)
def me(
    email: Annotated[str, Depends(current_user_email)],
    users: Annotated[Table, Depends(get_users_table)],
) -> ProfileResponse:
    user = find_user(users, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return profile_from_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    email: Annotated[str, Depends(current_user_email)],
    refresh_tokens: Annotated[Table, Depends(get_refresh_table)],
) -> None:
    revoke_all_refresh_tokens(refresh_tokens, email)


@router.post("/refresh", response_model=TokenResponse)
def refresh_session(
    payload: RefreshBody,
    users: Annotated[Table, Depends(get_users_table)],
    refresh_tokens: Annotated[Table, Depends(get_refresh_table)],
) -> TokenResponse:
    token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    email = token_payload["sub"]
    jti = token_payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    if find_user(users, email) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    if not refresh_token_active(refresh_tokens, jti, email):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    revoke_refresh_token(refresh_tokens, jti)
    return _issue_tokens(email, refresh_tokens)
