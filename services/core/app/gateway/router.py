"""Auth (OTP login), DigiLocker callback and Mitra (assisted) sessions."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.gateway import refresh as refresh_tokens
from app.gateway.models import AssistSession, User
from app.gateway.service import (
    AuthService, MitraService, MitraSessionError, OtpRateLimited, OtpRejected,
)
from app.shared import places
from app.shared.ratelimit import limit_code_checks, limit_code_requests
from app.shared.types import AssistSessionStatus, MitraScope, UserRole

router = APIRouter(prefix="/v1", tags=["Auth & Gateway"])

PHONE_PATTERN = r"^[0-9]{10}$"


EMAIL_PATTERN = r"^[^@\s]{1,64}@[^@\s]{1,120}\.[A-Za-z]{2,}$"


class OTPRequest(BaseModel):
    phone: Optional[str] = Field(None, pattern=PHONE_PATTERN, examples=["9876543210"])
    email: Optional[str] = Field(None, max_length=120, pattern=EMAIL_PATTERN)
    # Sign-in from the demo toggle. The demo code then works for seeded demo accounts only (never real ones).
    demo: bool = False


class OTPVerifyRequest(BaseModel):
    # Unknown fields (e.g. "role") are ignored: the role always comes from the users table.
    phone: Optional[str] = Field(None, pattern=PHONE_PATTERN)
    email: Optional[str] = Field(None, max_length=120, pattern=EMAIL_PATTERN)
    otp: str = Field(..., pattern=r"^[0-9]{6}$")
    demo: bool = False


class AuthUser(BaseModel):
    id: str
    name: str
    role: UserRole
    student_id: Optional[str] = None
    household_id: Optional[str] = None
    jurisdiction_state: Optional[str] = None
    jurisdiction_district: Optional[str] = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    # Spend it at /auth/refresh for the next access token (and the next refresh token) when this one expires.
    refresh_token: Optional[str] = None
    user: AuthUser


OFFICER_ROLE_CHOICES = (UserRole.INSTITUTE_OFFICER, UserRole.DISTRICT_OFFICER, UserRole.STATE_OFFICER,
                        UserRole.MINISTRY)


class CreateOfficerRequest(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=120, pattern=EMAIL_PATTERN)  # officers sign in with an emailed code
    phone: Optional[str] = Field(None, pattern=PHONE_PATTERN)
    role: UserRole
    jurisdiction_state: Optional[str] = Field(None, max_length=60)
    jurisdiction_district: Optional[str] = Field(None, max_length=60)
    institution_code: Optional[str] = Field(None, max_length=40)


class OfficerOut(AuthUser):
    email: Optional[str] = None
    phone: Optional[str] = None
    institution_code: Optional[str] = None
    is_active: bool
    is_demo: bool


class OfficerActive(BaseModel):
    model_config = {"extra": "forbid"}
    active: bool


class MitraSessionRequest(BaseModel):
    model_config = {"extra": "forbid"}
    student_id: str
    scope: MitraScope
    duration_minutes: int = Field(settings.MITRA_MAX_SESSION_MINUTES, ge=1, le=settings.MITRA_MAX_SESSION_MINUTES)


class MitraOtpVerifyRequest(BaseModel):
    otp: str = Field(..., pattern=r"^[0-9]{6}$")


class MitraSessionResponse(BaseModel):
    session_id: str
    student_id: str
    scope: MitraScope
    duration_minutes: int
    status: AssistSessionStatus
    started_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    @classmethod
    def of(cls, s: AssistSession) -> "MitraSessionResponse":
        return cls(session_id=s.id, student_id=s.student_id, scope=s.scope, duration_minutes=s.duration_minutes,
                   status=s.status, started_at=s.started_at, expires_at=s.expires_at)


def _user_out(user: User) -> AuthUser:
    return AuthUser(id=user.id, name=user.name, role=user.role, student_id=user.student_id,
                    household_id=user.household_id, jurisdiction_state=user.jurisdiction_state,
                    jurisdiction_district=user.jurisdiction_district)


@router.post("/auth/otp/request", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(limit_code_requests)])
async def request_otp(req: OTPRequest, db: AsyncSession = Depends(get_db)):
    """Send a login OTP by SMS or Email. The response is identical whether or not the account is registered."""
    if not (req.email or req.phone):
        raise HTTPException(status_code=422, detail="Give an email address or a mobile number")
    try:
        await AuthService(db).request_login_otp(phone=req.phone, email=req.email, demo=req.demo)
    except OtpRateLimited:
        raise HTTPException(status_code=429, detail="Too many codes requested. Try again in an hour.")
    contact = req.email.strip().lower() if req.email else f"{req.phone[:2]}******{req.phone[-2:]}"
    return {"status": "accepted", "message": f"If {contact} is registered, a sign-in code has been sent."}


@router.post("/auth/otp/verify", response_model=AuthTokenResponse, dependencies=[Depends(limit_code_checks)])
async def verify_otp(req: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, token, expires_in = await AuthService(db).verify_login_otp(phone=req.phone, email=req.email,
                                                                         otp=req.otp, demo=req.demo)
    except OtpRejected as exc:
        if exc.too_many_attempts:
            raise HTTPException(status_code=429, detail="Too many attempts. Request a new OTP.")
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    return await signed_in(db, user, token, expires_in)


async def signed_in(db: AsyncSession, user: User, token: Optional[str] = None,
                    expires_in: Optional[int] = None) -> AuthTokenResponse:
    """The sign-in answer for every way of signing in: an access token plus a refresh token."""
    from app.shared.security import create_access_token
    if token is None:
        token, expires_in = create_access_token(user.id, user.role.value)
    refresh = await refresh_tokens.issue(db, user.id)
    await db.commit()
    return AuthTokenResponse(access_token=token, expires_in=expires_in, refresh_token=refresh, user=_user_out(user))


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20, max_length=600)


@router.post("/auth/refresh", response_model=AuthTokenResponse, dependencies=[Depends(limit_code_checks)])
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Trade a refresh token for a new access token and a new refresh token (the old one stops working)."""
    from app.shared.security import create_access_token
    try:
        user, refresh = await refresh_tokens.rotate(db, body.refresh_token)
    except refresh_tokens.RefreshRejected:
        raise HTTPException(status_code=401, detail="Your session has ended. Sign in again.")
    token, expires_in = create_access_token(user.id, user.role.value)
    return AuthTokenResponse(access_token=token, expires_in=expires_in, refresh_token=refresh, user=_user_out(user))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Sign out on this device: the refresh token (and every token descended from it) stops working."""
    await refresh_tokens.revoke(db, body.refresh_token)


@router.post("/auth/register/start", status_code=status.HTTP_410_GONE, include_in_schema=False)
@router.post("/auth/register/complete", status_code=status.HTTP_410_GONE, include_in_schema=False)
async def phone_registration_retired():
    """Students sign up with DigiLocker (/v1/auth/digilocker/*), which confirms who they are."""
    raise HTTPException(status_code=410, detail="Sign up with DigiLocker in the ScholarSetu app")


@router.get("/geo/districts")
async def served_districts(db: AsyncSession = Depends(get_db)):
    """States and districts that have an officer on ScholarSetu, for registration pickers. Public: it
    lists place names only. A student elsewhere can still register, but no officer would see them yet."""
    from sqlalchemy import select
    rows = (await db.execute(select(User.jurisdiction_state, User.jurisdiction_district).where(
        User.is_active.is_(True), User.jurisdiction_state.is_not(None)).distinct())).all()
    served: dict[str, set[str]] = {}
    for state, district in rows:
        served.setdefault(places.tidy(state), set())
        if district:
            served[places.tidy(state)].add(places.tidy(district))
    return {"states": [{"state": s, "districts": sorted(d)} for s, d in sorted(served.items())]}


@router.get("/auth/me", response_model=AuthUser)
async def whoami(user: User = Depends(get_current_user)):
    return _user_out(user)


def _officer_out(u: User) -> OfficerOut:
    return OfficerOut(**_user_out(u).model_dump(), email=u.email, phone=u.phone, institution_code=u.institution_code,
                      is_active=u.is_active, is_demo=u.is_demo)


@router.get("/admin/officers", response_model=list[OfficerOut])
async def list_officers(admin: User = Depends(require_role(UserRole.MINISTRY)), db: AsyncSession = Depends(get_db)):
    """Every officer and Ministry account, newest first."""
    from sqlalchemy import select
    rows = (await db.execute(select(User).where(User.role.in_(OFFICER_ROLE_CHOICES))
                             .order_by(User.created_at.desc()))).scalars().all()
    return [_officer_out(u) for u in rows]


@router.post("/admin/officers", response_model=OfficerOut, status_code=status.HTTP_201_CREATED)
async def create_officer(req: CreateOfficerRequest, admin: User = Depends(require_role(UserRole.MINISTRY)),
                         db: AsyncSession = Depends(get_db)):
    """Enrol an officer. They sign in with a code emailed to them; an enrolled officer is never a demo account,
    so the demo code never works for them. District and institute officers need a state and district (their
    jurisdiction decides what they see); state officers need a state."""
    from sqlalchemy import or_, select
    if req.role not in OFFICER_ROLE_CHOICES:
        raise HTTPException(status_code=422, detail="Only officer and Ministry accounts can be enrolled here")
    needs_state = req.role != UserRole.MINISTRY
    needs_district = req.role in (UserRole.DISTRICT_OFFICER, UserRole.INSTITUTE_OFFICER)
    if needs_state and not (req.jurisdiction_state or "").strip():
        raise HTTPException(status_code=422, detail="Choose the state this officer works in")
    if needs_district and not (req.jurisdiction_district or "").strip():
        raise HTTPException(status_code=422, detail="Choose the district this officer works in")
    email = req.email.strip().lower()
    taken = await db.scalar(select(User.id).where(or_(User.email == email,
                                                      User.phone == req.phone if req.phone else False)))
    if taken:
        raise HTTPException(status_code=409, detail="An account with this email or mobile number already exists")
    user = User(name=req.name.strip(), email=email, phone=req.phone, role=req.role,
                jurisdiction_state=places.tidy(req.jurisdiction_state) if needs_state else None,
                jurisdiction_district=places.tidy(req.jurisdiction_district) if needs_district else None,
                institution_code=(req.institution_code or None) if req.role == UserRole.INSTITUTE_OFFICER else None,
                is_active=True, is_demo=False)
    db.add(user)
    await db.flush()
    from app.gateway.service import record_audit
    await record_audit(db, "OFFICER_CREATED", actor=admin,
                       details={"new_user_id": user.id, "role": req.role.value,
                                "state": user.jurisdiction_state, "district": user.jurisdiction_district})
    await db.commit()
    return _officer_out(user)


@router.post("/admin/officers/{user_id}/active", response_model=OfficerOut)
async def set_officer_active(user_id: str, body: OfficerActive,
                             admin: User = Depends(require_role(UserRole.MINISTRY)), db: AsyncSession = Depends(get_db)):
    """Deactivate (or reactivate) an officer. A deactivated account cannot sign in, and its open sessions stop
    working at their next request. You cannot deactivate yourself."""
    user = await db.get(User, user_id)
    if user is None or user.role not in OFFICER_ROLE_CHOICES:
        raise HTTPException(status_code=404, detail="Officer not found")
    if user.id == admin.id and not body.active:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own account")
    user.is_active = body.active
    from app.gateway.service import record_audit
    await record_audit(db, "OFFICER_ACTIVATED" if body.active else "OFFICER_DEACTIVATED", actor=admin,
                       details={"user_id": user.id})
    await db.commit()
    return _officer_out(user)


class DemoAccount(BaseModel):
    name: str
    role: UserRole
    email: Optional[str] = None
    phone: Optional[str] = None


class DemoInfo(BaseModel):
    available: bool
    demo_code: Optional[str] = None
    console_accounts: list[DemoAccount] = []
    app_accounts: list[DemoAccount] = []


@router.get("/auth/demo", response_model=DemoInfo)
async def demo_info(db: AsyncSession = Depends(get_db)):
    """For the demo toggle on every sign-in page: whether this server allows demo sign-in, and the seeded demo
    accounts it applies to. Real accounts never accept the demo code."""
    if not settings.DEMO_MODE:
        return DemoInfo(available=False)
    from sqlalchemy import select
    users = (await db.execute(select(User).where(User.is_demo.is_(True), User.is_active.is_(True))
                              .order_by(User.role, User.name))).scalars().all()
    officer = set(OFFICER_ROLE_CHOICES)
    return DemoInfo(
        available=True, demo_code=settings.DEMO_OTP,
        console_accounts=[DemoAccount(name=u.name, role=u.role, email=u.email) for u in users
                          if u.role in officer and u.email],
        app_accounts=[DemoAccount(name=u.name, role=u.role, phone=u.phone) for u in users
                      if u.role not in officer or u.role == UserRole.MINISTRY])


def _mitra_error(exc: MitraSessionError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/mitra/sessions", response_model=MitraSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_mitra_session(
    req: MitraSessionRequest,
    mitra: User = Depends(require_role(UserRole.MITRA)),
    db: AsyncSession = Depends(get_db),
):
    """Request an assist session. It stays PENDING_STUDENT_OTP until the student's OTP is verified."""
    try:
        session = await MitraService(db).request_session(mitra, req.student_id, req.scope, req.duration_minutes)
    except MitraSessionError as exc:
        raise _mitra_error(exc)
    return MitraSessionResponse.of(session)


@router.post("/mitra/sessions/{session_id}/verify", response_model=MitraSessionResponse)
async def verify_mitra_session(
    session_id: str,
    req: MitraOtpVerifyRequest,
    mitra: User = Depends(require_role(UserRole.MITRA)),
    db: AsyncSession = Depends(get_db),
):
    """Submit the OTP the student received. Activates the session and starts its timer."""
    try:
        session = await MitraService(db).verify_student_otp(mitra, session_id, req.otp)
    except MitraSessionError as exc:
        raise _mitra_error(exc)
    return MitraSessionResponse.of(session)


@router.get("/mitra/sessions/{session_id}", response_model=MitraSessionResponse)
async def get_mitra_session(
    session_id: str,
    mitra: User = Depends(require_role(UserRole.MITRA)),
    db: AsyncSession = Depends(get_db),
):
    try:
        session = await MitraService(db).get_owned_session(session_id, mitra)
    except MitraSessionError as exc:
        raise _mitra_error(exc)
    return MitraSessionResponse.of(session)


@router.delete("/mitra/sessions/{session_id}", response_model=MitraSessionResponse)
async def end_mitra_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End a session. Allowed for the helper who opened it and for the student it acts for."""
    try:
        session = await MitraService(db).end_session(user, session_id)
    except MitraSessionError as exc:
        raise _mitra_error(exc)
    return MitraSessionResponse.of(session)
