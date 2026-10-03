"""Refresh tokens: keep a person signed in past the 15-minute access token without asking for a new code.

Only a SHA-256 of the token is stored. Using a token revokes it and issues the next one in the same family. Using
a token a second time means it was copied, so the whole family is revoked and the person signs in again. A token
expires after REFRESH_TOKEN_DAYS idle, and stops working the moment the account is deactivated."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.gateway.models import RefreshToken, User
from app.shared.ids import new_id


class RefreshRejected(Exception):
    """The token is unknown, used, revoked, expired or its account is inactive: sign in again."""


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def issue(db: AsyncSession, user_id: str, family_id: Optional[str] = None) -> str:
    """Create a refresh token (a new family unless one is given). The caller commits."""
    raw = secrets.token_urlsafe(48)
    db.add(RefreshToken(user_id=user_id, family_id=family_id or new_id(), token_hash=_hash(raw),
                        expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_DAYS)))
    await db.flush()
    return raw


async def _revoke_family(db: AsyncSession, family_id: str) -> None:
    await db.execute(update(RefreshToken).where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
                     .values(revoked_at=_now()))


async def rotate(db: AsyncSession, raw: str) -> tuple[User, str]:
    """Spend a refresh token. Returns the user and the next token. Commits."""
    row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw))
                            .with_for_update())).scalar_one_or_none()
    if row is None:
        raise RefreshRejected()
    if row.used_at is not None or row.revoked_at is not None:
        await _revoke_family(db, row.family_id)  # a spent token turning up again: assume it leaked
        await db.commit()
        raise RefreshRejected()
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    user = await db.get(User, row.user_id)
    if expires < _now() or user is None or not user.is_active:
        raise RefreshRejected()
    row.used_at = _now()
    new = await issue(db, user.id, row.family_id)
    await db.commit()
    return user, new


async def revoke(db: AsyncSession, raw: str) -> None:
    """Sign out: revoke the whole family of this token. Unknown tokens are ignored."""
    row = (await db.execute(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw)))).scalar_one_or_none()
    if row is not None:
        await _revoke_family(db, row.family_id)
        await db.commit()


async def purge(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Delete tokens that can no longer be used (expired, or spent/revoked more than a day ago)."""
    from sqlalchemy import delete, or_
    now = now or _now()
    day_ago = now - timedelta(days=1)
    res = await db.execute(delete(RefreshToken).where(or_(
        RefreshToken.expires_at < now, RefreshToken.used_at < day_ago, RefreshToken.revoked_at < day_ago)))
    return res.rowcount or 0
