"""Retention: delete what has no further use, so the database does not keep personal data (login attempts, access
tokens, delivery receipts) longer than the work needs. Runs from the always-on worker (RETENTION_INTERVAL_SECONDS).

Never touched: the ledger, applications, payments, attestations, consents and the audit log. Those are records of
decisions and money, kept under their own rules."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.digilocker.models import DigiLockerLogin, DigiLockerSession
from app.gateway import refresh as refresh_tokens
from app.gateway.models import OtpChallenge
from app.ledger.models import OutboxMessage
from app.nudge.models import Notification
from app.sync.models import SyncReceipt

logger = logging.getLogger("scholarsetu.retention")

# Days a row is kept after it stopped being useful (expired, published, read).
LOGIN_ATTEMPT_DAYS = 1          # login codes and DigiLocker sign-in attempts
DIGILOCKER_SESSION_DAYS = 7     # import sessions (the access token itself is cleared the moment the session expires)
SYNC_RECEIPT_DAYS = 30          # a resent offline action is answered from its receipt; a phone is not offline for longer
OUTBOX_DAYS = 7                 # published events (already delivered to the bus)
READ_NOTIFICATION_DAYS = 90
ANY_NOTIFICATION_DAYS = 365


async def purge_expired(db: AsyncSession, now: Optional[datetime] = None) -> dict[str, int]:
    """Delete expired rows. Returns how many were removed (or cleared) per kind. The caller commits."""
    now = now or datetime.now(timezone.utc)
    ago = lambda days: now - timedelta(days=days)  # noqa: E731
    counts: dict[str, int] = {}

    async def run(name: str, statement) -> None:
        counts[name] = (await db.execute(statement)).rowcount or 0

    await run("login_codes", delete(OtpChallenge).where(OtpChallenge.expires_at < ago(LOGIN_ATTEMPT_DAYS)))
    await run("digilocker_sign_ins", delete(DigiLockerLogin).where(DigiLockerLogin.expires_at < ago(LOGIN_ATTEMPT_DAYS)))
    # A student who connected DigiLocker but never imported leaves an access token behind: clear it once the session ends.
    await run("digilocker_tokens_cleared", update(DigiLockerSession).where(
        DigiLockerSession.expires_at < now, DigiLockerSession.access_token.is_not(None)).values(access_token=None))
    await run("digilocker_sessions", delete(DigiLockerSession).where(
        DigiLockerSession.expires_at < ago(DIGILOCKER_SESSION_DAYS)))
    await run("sync_receipts", delete(SyncReceipt).where(SyncReceipt.created_at < ago(SYNC_RECEIPT_DAYS)))
    await run("outbox", delete(OutboxMessage).where(
        OutboxMessage.published_at.is_not(None), OutboxMessage.published_at < ago(OUTBOX_DAYS)))
    await run("notifications_read", delete(Notification).where(
        Notification.read_at.is_not(None), Notification.read_at < ago(READ_NOTIFICATION_DAYS)))
    await run("notifications_old", delete(Notification).where(Notification.created_at < ago(ANY_NOTIFICATION_DAYS)))
    counts["refresh_tokens"] = await refresh_tokens.purge(db, now)
    return counts
