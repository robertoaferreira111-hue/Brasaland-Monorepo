"""Login, logout, refresh, current user, and password recovery."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from tinydb.table import Table

from app.config import Settings, get_settings
from app.database import (
    authenticate_user,
    find_user,
    get_refresh_table,
    get_reset_tokens_table,
    get_users_table,
    profile_from_user,
    refresh_token_active,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    store_refresh_token,
    update_user_password,
)
from app.deps import current_user_email
from app.email import EmailDeliveryError, send_password_reset_email
from app.models import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginBody,
    MessageResponse,
    ProfileResponse,
    RefreshBody,
    ResetPasswordRequest,
    TokenResponse,
)
from app.rate_limit import allow_forgot_password
from app.reset_tokens import (
    consume_valid_token,
    invalidate_user_tokens,
    issue_reset_token,
    mark_token_used,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

FORGOT_PASSWORD_MESSAGE = (
    "If that address is registered, you'll receive a link shortly."
)


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


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    users: Annotated[Table, Depends(get_users_table)],
    tokens: Annotated[Table, Depends(get_reset_tokens_table)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    """Always return the same confirmation. Send email only for known accounts."""
    user = find_user(users, payload.email)
    if user is None:
        return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)

    # Same public response when throttled so enumeration stays closed.
    if not allow_forgot_password(payload.email):
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
    refresh_tokens: Annotated[Table, Depends(get_refresh_table)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    if len(payload.new_password) < settings.min_password_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"new_password must be at least {settings.min_password_length} characters"
            ),
        )

    # Conditionally consume first so concurrent resets cannot both succeed.
    record = consume_valid_token(tokens, payload.token)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    updated = update_user_password(users, record["user_id"], payload.new_password)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    invalidate_user_tokens(tokens, record["user_id"])
    revoke_all_refresh_tokens(refresh_tokens, updated["email"])
    return MessageResponse(message="Password has been reset successfully.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    email: Annotated[str, Depends(current_user_email)],
    users: Annotated[Table, Depends(get_users_table)],
    tokens: Annotated[Table, Depends(get_reset_tokens_table)],
    refresh_tokens: Annotated[Table, Depends(get_refresh_table)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    if len(payload.new_password) < settings.min_password_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"new_password must be at least {settings.min_password_length} characters"
            ),
        )

    user = find_user(users, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if not verify_password(
        payload.current_password,
        user["password_salt"],
        user["password_digest"],
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    update_user_password(users, user["id"], payload.new_password)
    invalidate_user_tokens(tokens, user["id"])
    revoke_all_refresh_tokens(refresh_tokens, user["email"])
    return MessageResponse(message="Password has been changed successfully.")
