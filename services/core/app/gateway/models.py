"""Identity, OTP, Mitra assist-session, audit and outbound-SMS tables."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id
from app.shared.types import AssistSessionStatus, MitraScope, OtpPurpose, UserRole


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    phone: Mapped[Optional[str]] = mapped_column(String(15), unique=True, index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), unique=True, index=True, nullable=True)
    # Set when the account signs in with DigiLocker (the DigiLocker id from the partner token response).
    digilocker_id: Mapped[Optional[str]] = mapped_column(String(80), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, name="user_role"), nullable=False)
    # Set for STUDENT users: the student record this login belongs to.
    student_id: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    # Set for GUARDIAN users: the household they may view.
    household_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Officer jurisdiction: STATE_OFFICER needs a state; DISTRICT/INSTITUTE officers a state and district.
    # MINISTRY is national. Officers only see students inside their jurisdiction.
    jurisdiction_state: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    jurisdiction_district: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # INSTITUTE_OFFICER: the UDISE+/AISHE code of their institution (Reach Radar outreach lists).
    institution_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Only seeded demo users may use DEMO_OTP, and only while DEMO_MODE=true.
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    phone: Mapped[Optional[str]] = mapped_column(String(15), index=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), index=True, nullable=True)
    purpose: Mapped[OtpPurpose] = mapped_column(SAEnum(OtpPurpose, name="otp_purpose"), nullable=False)
    # For MITRA_CONSENT: the assist session this OTP approves.
    subject_ref: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    # Rate limits count recent challenges and failures per phone/email and purpose.
    __table_args__ = (
        Index("ix_otp_challenges_phone_purpose_created", "phone", "purpose", "created_at"),
        Index("ix_otp_challenges_email_purpose_created", "email", "purpose", "created_at"),
    )


class AssistSession(Base):
    __tablename__ = "assist_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    mitra_user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    student_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    scope: Mapped[MitraScope] = mapped_column(SAEnum(MitraScope, name="mitra_scope"), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AssistSessionStatus] = mapped_column(
        SAEnum(AssistSessionStatus, name="assist_session_status"), nullable=False
    )
    student_otp_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, index=True, nullable=False)
    student_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    assist_session_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class OutboundSms(Base):
    """Simulated SMS gateway: messages are stored instead of being sent."""
    __tablename__ = "outbound_sms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    to_phone: Mapped[str] = mapped_column(String(15), index=True, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
