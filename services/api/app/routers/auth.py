"""Password recovery, reset, change, and supporting login routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from tinydb.table import Table

from app.auth_models import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    ResetPasswordRequest,
)
from app.config import Settings, get_settings
from app.database import get_reset_tokens_table, get_users_table
from app.email import EmailDeliveryError, send_password_reset_email
from app.rate_limit import allow_forgot_password
from app.reset_tokens import (
    consume_valid_token,
    invalidate_user_tokens,
    issue_reset_token,
    mark_token_used,
)
from app.security import (
    create_access_token,
    get_current_user,
    verify_password,
)
from app.users import get_user_by_email, normalize_email, update_password

router = APIRouter(prefix="/auth", tags=["auth"])

FORGOT_PASSWORD_MESSAGE = (
    "If that address is registered, you'll receive a link shortly."
)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    users: Annotated[Table, Depends(get_users_table)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    user = get_user_by_email(users, payload.email)
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(subject=user["email"], settings=settings)
    return LoginResponse(access_token=token, email=user["email"])


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    users: Annotated[Table, Depends(get_users_table)],
    tokens: Annotated[Table, Depends(get_reset_tokens_table)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    """Always return the same confirmation. Send email only for known accounts."""
    email = normalize_email(str(payload.email))
    user = get_user_by_email(users, email)
    if user is None:
        return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)

    # Same public response when throttled so enumeration stays closed.
    if not allow_forgot_password(email):
        return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)

    raw_token, token_id = issue_reset_token(
        tokens,
        user_id=user["id"],
        expire_minutes=settings.reset_token_expire_minutes,
    )
    try:
        send_password_reset_email(
            to_email=user["email"],
            raw_token=raw_token,
            settings=settings,
        )
    except EmailDeliveryError as exc:
        # Do not claim delivery succeeded when the provider failed.
        mark_token_used(tokens, token_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send recovery email. Please try again later.",
        ) from exc

    return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    users: Annotated[Table, Depends(get_users_table)],
    tokens: Annotated[Table, Depends(get_reset_tokens_table)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    if len(payload.new_password) < settings.min_password_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"new_password must be at least {settings.min_password_length} characters",
        )

    # Conditionally consume first so concurrent resets cannot both succeed.
    record = consume_valid_token(tokens, payload.token)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    updated = update_password(users, record["user_id"], payload.new_password)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    invalidate_user_tokens(tokens, record["user_id"])
    return MessageResponse(message="Password has been reset successfully.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    users: Annotated[Table, Depends(get_users_table)],
    tokens: Annotated[Table, Depends(get_reset_tokens_table)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    if len(payload.new_password) < settings.min_password_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"new_password must be at least {settings.min_password_length} characters",
        )
    if not verify_password(payload.current_password, current_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    update_password(users, current_user["id"], payload.new_password)
    invalidate_user_tokens(tokens, current_user["id"])
    return MessageResponse(message="Password has been changed successfully.")
