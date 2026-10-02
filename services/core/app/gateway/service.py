"""Authentication (OTP login), Mitra assist sessions, audit logging and the simulated SMS gateway."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.gateway.models import AssistSession, AuditLog, OtpChallenge, OutboundSms, User
from app.shared.ids import new_id
from app.shared.security import create_access_token, generate_otp, hash_otp, otp_matches
from app.shared.types import AssistSessionStatus, MitraScope, OtpPurpose, UserRole

logger = logging.getLogger("scholarsetu.gateway")

_SCOPE_LABELS = {
    MitraScope.UPLOAD_DOCUMENTS: "upload documents",
    MitraScope.VIEW_STATUS: "view your application status",
    MitraScope.RESPOND_DEFICIENCY: "respond to a deficiency",
}


class OtpRateLimited(Exception):
    """Too many codes requested for this phone recently."""


class OtpRejected(Exception):
    """OTP verification failed. `too_many_attempts` distinguishes lockout from a plain mismatch."""

    def __init__(self, too_many_attempts: bool = False):
        super().__init__("too many attempts" if too_many_attempts else "invalid or expired OTP")
        self.too_many_attempts = too_many_attempts


class MitraSessionError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def record_audit(
    db: AsyncSession,
    action: str,
    *,
    actor: Optional[User] = None,
    student_id: Optional[str] = None,
    assist_session_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> None:
    db.add(AuditLog(
        action=action,
        actor_user_id=actor.id if actor else None,
        actor_role=actor.role.value if actor else None,
        student_id=student_id,
        assist_session_id=assist_session_id,
        details=details or {},
    ))


async def send_sms(db: AsyncSession, to_phone: str, body: str, category: str) -> None:
    """Simulated gateway: store the message. The body is never logged because it may contain an OTP."""
    db.add(OutboundSms(to_phone=to_phone, body=body, category=category))
    logger.info("SMS queued category=%s to=%s******%s", category, to_phone[:2], to_phone[-2:])


async def _recent(db: AsyncSession, contact: str, purpose: OtpPurpose, what):
    cond = OtpChallenge.email == contact if '@' in contact else OtpChallenge.phone == contact
    return await db.scalar(select(what).select_from(OtpChallenge).where(
        cond, OtpChallenge.purpose == purpose,
        OtpChallenge.created_at >= _now() - timedelta(hours=1))) or 0


async def _issue_challenge(db: AsyncSession, contact: str, purpose: OtpPurpose, subject_ref: Optional[str]) -> str:
    """Invalidate earlier open challenges for the same target and create a fresh one. Returns the plain OTP.
    Raises OtpRateLimited after OTP_REQUESTS_PER_HOUR codes for this contact and purpose."""
    cond = OtpChallenge.email == contact if '@' in contact else OtpChallenge.phone == contact
    phone, email = (None, contact) if '@' in contact else (contact, None)

    if await _recent(db, contact, purpose, func.count()) >= settings.OTP_REQUESTS_PER_HOUR:
        raise OtpRateLimited()

    await db.execute(
        update(OtpChallenge)
        .where(cond, OtpChallenge.purpose == purpose,
               OtpChallenge.subject_ref == subject_ref, OtpChallenge.consumed_at.is_(None))
        .values(consumed_at=_now())
    )
    challenge_id = new_id()
    otp = generate_otp()
    db.add(OtpChallenge(
        id=challenge_id, phone=phone, email=email, purpose=purpose, subject_ref=subject_ref,
        otp_hash=hash_otp(challenge_id, otp),
        expires_at=_now() + timedelta(minutes=settings.OTP_TTL_MINUTES),
    ))
    return otp


async def _check_challenge(db: AsyncSession, contact: str, purpose: OtpPurpose,
                           subject_ref: Optional[str], otp: str) -> None:
    """Verify the latest open challenge. Consumes it on success; counts the attempt on failure."""
    cond = OtpChallenge.email == contact if '@' in contact else OtpChallenge.phone == contact
    result = await db.execute(
        select(OtpChallenge)
        .where(cond, OtpChallenge.purpose == purpose,
               OtpChallenge.subject_ref == subject_ref, OtpChallenge.consumed_at.is_(None))
        .order_by(OtpChallenge.created_at.desc())
        .limit(1)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    challenge = result.scalar_one_or_none()

    if await _recent(db, contact, purpose, func.coalesce(func.sum(OtpChallenge.attempts), 0)) \
            >= settings.OTP_FAILURES_PER_HOUR:
        raise OtpRejected(too_many_attempts=True)
    if challenge is None or challenge.consumed_at is not None or _as_aware(challenge.expires_at) < _now():
        raise OtpRejected()
    if challenge.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise OtpRejected(too_many_attempts=True)
    if not otp_matches(challenge.id, otp, challenge.otp_hash):
        challenge.attempts += 1
        await db.commit()
        raise OtpRejected(too_many_attempts=challenge.attempts >= settings.OTP_MAX_ATTEMPTS)
    challenge.consumed_at = _now()


def demo_login_allowed(user: User, demo: bool) -> bool:
    """The demo code signs in only a seeded demo account (is_demo), only when the server allows demo mode, and
    only when the sign-in came from the demo toggle. Real accounts always need the code that was sent to them,
    and a demo account with the toggle off gets a real code too."""
    return settings.DEMO_MODE and demo and user.is_demo


def normalise_email(email: Optional[str]) -> Optional[str]:
    return email.strip().lower() if email else None


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _active_user_by_contact(self, contact: str) -> Optional[User]:
        cond = User.email == contact if "@" in contact else User.phone == contact
        result = await self.db.execute(select(User).where(cond, User.is_active.is_(True)))
        return result.scalar_one_or_none()

    async def request_login_otp(self, phone: Optional[str] = None, email: Optional[str] = None,
                                demo: bool = False) -> None:
        """Send a code if the account is active. Callers get the same answer either way.
        Demo sign-in of a demo account sends nothing: the demo code is used instead."""
        from app.gateway.email import send_login_code
        contact = normalise_email(email) or phone
        if not contact:
            return
        user = await self._active_user_by_contact(contact)
        if user is None or demo_login_allowed(user, demo):
            return
        otp = await _issue_challenge(self.db, contact, OtpPurpose.LOGIN, None)
        await self.db.commit()  # the challenge exists before the code leaves, so it can always be checked
        if "@" in contact:
            await send_login_code(contact, otp)
        else:
            await send_sms(self.db, contact, f"ScholarSetu login code: {otp}. Valid for "
                           f"{settings.OTP_TTL_MINUTES} minutes. Do not share it.", "OTP_LOGIN")
            await self.db.commit()

    async def verify_login_otp(self, phone: Optional[str] = None, email: Optional[str] = None,
                               otp: str = "", demo: bool = False) -> tuple[User, str, int]:
        contact = normalise_email(email) or phone
        if not contact:
            raise OtpRejected()
        user = await self._active_user_by_contact(contact)
        if user is None:
            raise OtpRejected()  # an unregistered account is never signed in
        demo_used = demo_login_allowed(user, demo) and otp == settings.DEMO_OTP
        if not demo_used:
            await _check_challenge(self.db, contact, OtpPurpose.LOGIN, None, otp)
        token, expires_in = create_access_token(user.id, user.role.value)
        await record_audit(self.db, "LOGIN", actor=user, student_id=user.student_id,
                           details={"demo_otp": demo_used, "via": "email" if "@" in contact else "sms"})
        await self.db.commit()
        return user, token, expires_in


class MitraService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _student_user(self, student_id: str) -> User:
        result = await self.db.execute(
            select(User).where(User.student_id == student_id, User.role == UserRole.STUDENT,
                               User.is_active.is_(True))
        )
        student = result.scalar_one_or_none()
        if student is None:
            raise MitraSessionError(404, "Student not found")
        return student

    async def get_owned_session(self, session_id: str, mitra: User) -> AssistSession:
        session = await self.db.get(AssistSession, session_id)
        if session is None or session.mitra_user_id != mitra.id:
            raise MitraSessionError(404, "Session not found")
        return session

    async def request_session(self, mitra: User, student_id: str, scope: MitraScope,
                              duration_minutes: int) -> AssistSession:
        student = await self._student_user(student_id)
        session = AssistSession(
            id=new_id(), mitra_user_id=mitra.id, student_id=student_id, scope=scope,
            duration_minutes=duration_minutes, status=AssistSessionStatus.PENDING_STUDENT_OTP,
        )
        self.db.add(session)
        try:
            otp = await _issue_challenge(self.db, student.phone, OtpPurpose.MITRA_CONSENT, session.id)
        except OtpRateLimited:
            raise MitraSessionError(429, "Too many consent codes were sent to this student recently. Try later.")
        await send_sms(
            self.db, student.phone,
            f"ScholarSetu: {mitra.name} wants to {_SCOPE_LABELS[scope]} for you for "
            f"{duration_minutes} minutes. Share code {otp} with them only if you agree.",
            "OTP_MITRA_CONSENT",
        )
        await record_audit(self.db, "MITRA_SESSION_REQUESTED", actor=mitra, student_id=student_id,
                           assist_session_id=session.id,
                           details={"scope": scope.value, "duration_minutes": duration_minutes})
        await self.db.commit()
        return session

    async def verify_student_otp(self, mitra: User, session_id: str, otp: str) -> AssistSession:
        session = await self.get_owned_session(session_id, mitra)
        if session.status != AssistSessionStatus.PENDING_STUDENT_OTP:
            raise MitraSessionError(409, f"Session is {session.status.value}")
        student = await self._student_user(session.student_id)
        try:
            await _check_challenge(self.db, student.phone, OtpPurpose.MITRA_CONSENT, session.id, otp)
        except OtpRejected as exc:
            await record_audit(self.db, "MITRA_SESSION_OTP_FAILED", actor=mitra, student_id=session.student_id,
                               assist_session_id=session.id)
            await self.db.commit()
            raise MitraSessionError(429 if exc.too_many_attempts else 401,
                                    "Too many attempts" if exc.too_many_attempts else "Invalid or expired OTP")
        now = _now()
        session.status = AssistSessionStatus.ACTIVE
        session.student_otp_verified = True
        session.started_at = now
        session.expires_at = now + timedelta(minutes=session.duration_minutes)
        await record_audit(self.db, "MITRA_SESSION_STARTED", actor=mitra, student_id=session.student_id,
                           assist_session_id=session.id,
                           details={"scope": session.scope.value, "expires_at": session.expires_at.isoformat()})
        await self.db.commit()
        return session

    async def end_session(self, actor: User, session_id: str) -> AssistSession:
        session = await self.db.get(AssistSession, session_id)
        if session is None or actor.id != session.mitra_user_id and actor.student_id != session.student_id:
            raise MitraSessionError(404, "Session not found")
        if session.status != AssistSessionStatus.ENDED:
            session.status = AssistSessionStatus.ENDED
            session.ended_at = _now()
            await record_audit(self.db, "MITRA_SESSION_ENDED", actor=actor, student_id=session.student_id,
                               assist_session_id=session.id)
            await self.db.commit()
        return session
