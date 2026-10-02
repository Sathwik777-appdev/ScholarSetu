"""Sign-in codes by email for the officer and Ministry console (Microsoft 365 SMTP, STARTTLS).

Sender and server come from settings (SMTP_*); the password from Secret Manager (SMTP_PASSWORD). Without a
password nothing is sent and a warning is logged: real officers then cannot receive a code, which is visible
in the logs rather than silently pretending to work. The code itself is never logged."""

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.config import settings

logger = logging.getLogger("scholarsetu.email")


def _mask(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:2]}***@{domain}"


def _message(to_email: str, otp: str) -> EmailMessage:
    minutes = settings.OTP_TTL_MINUTES
    msg = EmailMessage()
    msg["Subject"] = f"{otp} is your ScholarSetu sign-in code"
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM or settings.SMTP_USERNAME or ""))
    msg["To"] = to_email
    msg.set_content(f"Your ScholarSetu sign-in code is {otp}.\n\nIt expires in {minutes} minutes. "
                    "ScholarSetu staff will never ask you for this code.\n\n"
                    "If you did not try to sign in, ignore this email.\n\n— ScholarSetu, Ministry of Tribal Affairs")
    msg.add_alternative(f"""<!doctype html><html><body style="margin:0;background:#f4f6fb;font-family:Segoe UI,Arial,sans-serif;color:#0f172a">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 16px">
<table role="presentation" width="480" cellpadding="0" cellspacing="0" style="max-width:480px;background:#ffffff;border-radius:16px;overflow:hidden">
<tr><td style="background:#0c1326;padding:20px 28px;color:#ffffff;font-size:18px;font-weight:600">
<span style="display:inline-block;background:#f59e0b;color:#0c1326;border-radius:8px;padding:2px 8px;margin-right:8px">◠</span>ScholarSetu</td></tr>
<tr><td style="padding:28px">
<p style="margin:0 0 8px;font-size:15px">Your sign-in code for the officer and Ministry console:</p>
<p style="margin:16px 0;font-size:34px;letter-spacing:10px;font-weight:700;color:#0c1326">{otp}</p>
<p style="margin:0 0 8px;font-size:14px;color:#475569">It expires in {minutes} minutes. ScholarSetu staff will never ask you for this code.</p>
<p style="margin:16px 0 0;font-size:13px;color:#64748b">If you did not try to sign in, ignore this email; your account is safe.</p>
</td></tr>
<tr><td style="padding:16px 28px;background:#f8fafc;font-size:12px;color:#64748b">ScholarSetu · Ministry of Tribal Affairs scholarships</td></tr>
</table></td></tr></table></body></html>""", subtype="html")
    return msg


def _send_sync(msg: EmailMessage) -> None:
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)


async def send_login_code(to_email: str, otp: str) -> bool:
    """Email a sign-in code. Returns whether the mail server accepted it."""
    if not (settings.SMTP_USERNAME and settings.SMTP_PASSWORD):
        logger.warning("SMTP is not configured; no sign-in code was emailed to %s", _mask(to_email))
        return False
    try:
        await asyncio.to_thread(_send_sync, _message(to_email, otp))
    except Exception as exc:  # noqa: BLE001 - the caller answers the same either way; the failure is logged
        logger.error("emailing a sign-in code to %s failed: %s", _mask(to_email), type(exc).__name__)
        return False
    logger.info("sign-in code emailed to %s", _mask(to_email))
    return True
