"""Transactional email delivery (Resend preferred, SendGrid optional)."""

from __future__ import annotations

import html
import logging

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when the configured provider rejects or fails a send."""


def build_reset_link(frontend_url: str, raw_token: str) -> str:
    base = frontend_url.rstrip("/")
    return f"{base}/reset-password?token={raw_token}"


def build_reset_email_body(*, reset_link: str, expire_minutes: int) -> str:
    return (
        "You requested a password reset for your Brasaland account.\n\n"
        f"Open this link to choose a new password (expires in {expire_minutes} minutes):\n"
        f"{reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )


def build_reset_email_html(*, reset_link: str, expire_minutes: int) -> str:
    safe_link = html.escape(reset_link, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
  <body style="margin:0;padding:0;background:#f5f5f4;color:#0c0a09;font-family:Georgia,serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f5f4;padding:24px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;background:#ffffff;border:1px solid #d6d3d1;border-radius:16px;padding:28px;">
            <tr>
              <td>
                <p style="margin:0 0 8px;font-size:28px;font-weight:700;color:#7c2d12;">Brasaland</p>
                <h1 style="margin:0 0 12px;font-size:22px;">Reset your password</h1>
                <p style="margin:0 0 16px;line-height:1.5;font-family:Segoe UI,sans-serif;">
                  You requested a password reset for your Brasaland account.
                  This link expires in {expire_minutes} minutes.
                </p>
                <p style="margin:0 0 20px;">
                  <a href="{safe_link}" style="display:inline-block;background:#7c2d12;color:#fff7ed;text-decoration:none;padding:12px 18px;border-radius:999px;font-family:Segoe UI,sans-serif;font-weight:600;">
                    Choose a new password
                  </a>
                </p>
                <p style="margin:0 0 8px;line-height:1.5;font-size:14px;color:#57534e;font-family:Segoe UI,sans-serif;">
                  Or paste this URL into your browser:
                </p>
                <p style="margin:0 0 16px;word-break:break-all;font-size:13px;font-family:Segoe UI,sans-serif;">
                  <a href="{safe_link}" style="color:#7c2d12;">{safe_link}</a>
                </p>
                <p style="margin:0;line-height:1.5;font-size:13px;color:#57534e;font-family:Segoe UI,sans-serif;">
                  If you did not request this, you can ignore this email.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_password_reset_email(
    *,
    to_email: str,
    raw_token: str,
    settings: Settings | None = None,
) -> None:
    cfg = settings or get_settings()
    reset_link = build_reset_link(cfg.frontend_url, raw_token)
    subject = "Reset your Brasaland password"
    text_body = build_reset_email_body(
        reset_link=reset_link,
        expire_minutes=cfg.reset_token_expire_minutes,
    )
    html_body = build_reset_email_html(
        reset_link=reset_link,
        expire_minutes=cfg.reset_token_expire_minutes,
    )

    if cfg.email_provider == "resend":
        _send_resend(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            settings=cfg,
        )
        return
    if cfg.email_provider == "sendgrid":
        _send_sendgrid(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            settings=cfg,
        )
        return
    raise EmailDeliveryError("No email provider configured (set RESEND_API_KEY)")


def _send_resend(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    settings: Settings,
) -> None:
    assert settings.resend_api_key
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": settings.email_from,
            "to": [to_email],
            "subject": subject,
            "text": text_body,
            "html": html_body,
        },
        timeout=20.0,
    )
    if response.status_code >= 400:
        logger.error("Resend email failed status=%s", response.status_code)
        raise EmailDeliveryError("Email provider rejected the message")


def _send_sendgrid(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    settings: Settings,
) -> None:
    assert settings.sendgrid_api_key
    response = httpx.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": _sendgrid_from_email(settings.email_from)},
            "subject": subject,
            "content": [
                {"type": "text/plain", "value": text_body},
                {"type": "text/html", "value": html_body},
            ],
        },
        timeout=20.0,
    )
    if response.status_code >= 400:
        logger.error("SendGrid email failed status=%s", response.status_code)
        raise EmailDeliveryError("Email provider rejected the message")


def _sendgrid_from_email(email_from: str) -> str:
    """Accept 'Name <email@domain>' or bare email for SendGrid's from.email."""
    value = email_from.strip()
    if "<" in value and value.endswith(">"):
        return value.split("<", 1)[1][:-1].strip()
    return value
