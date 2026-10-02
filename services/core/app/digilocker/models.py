from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DigiLockerSession(Base):
    """One "Get from DigiLocker" attempt: the OAuth state and PKCE verifier, then (briefly) the access token.

    The token is cleared once the student has imported documents, and the session expires after
    SESSION_MINUTES; it is never returned by the API."""
    __tablename__ = "digilocker_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")  # PENDING|CONNECTED|FAILED|DONE
    access_token: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    digilocker_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DigiLockerLogin(Base):
    """One "Sign in with DigiLocker" attempt (OAuth 2.0 + PKCE). The client secret and the token exchange stay on
    the server; the app only relays the code. A new person gets a single-use registration token for the short
    sign-up step; it and the attempt expire after LOGIN_MINUTES."""
    __tablename__ = "digilocker_logins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    state: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")  # PENDING|NEEDS_SIGNUP|DONE|FAILED
    digilocker_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    profile: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)     # name, dob, gender from DigiLocker
    registration_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
