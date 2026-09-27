"""Auth (OTP login), DigiLocker callback and Mitra (assisted) sessions."""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.gateway.models import AssistSession, User
from app.gateway.service import (
    AuthService, MitraService, MitraSessionError, OtpRejected, RegistrationError, RegistrationService,
)
from app.shared.types import AssistSessionStatus, Gender, MitraScope, UserRole

router = APIRouter(prefix="/v1", tags=["Auth & Gateway"])

PHONE_PATTERN = r"^[0-9]{10}$"


class OTPRequest(BaseModel):
    phone: str = Field(..., pattern=PHONE_PATTERN, examples=["9876543210"])


class OTPVerifyRequest(BaseModel):
    # Unknown fields (e.g. "role") are ignored: the role always comes from the users table.
    phone: str = Field(..., pattern=PHONE_PATTERN)
    otp: str = Field(..., pattern=r"^[0-9]{6}$")


class RegistrationComplete(BaseModel):
    model_config = {"extra": "forbid"}
    phone: str = Field(..., pattern=PHONE_PATTERN)
    otp: str = Field(..., pattern=r"^[0-9]{6}$")
    full_name: str = Field(..., min_length=2, max_length=100)
    dob: date
    gender: Gender
    state: str = Field(..., min_length=2, max_length=60)
    district: str = Field(..., min_length=2, max_length=60)
    father_name: Optional[str] = Field(None, max_length=100)
    preferred_language: str = Field("hi", pattern=r"^[a-z]{2,3}$")


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
    user: AuthUser


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


@router.post("/auth/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(req: OTPRequest, db: AsyncSession = Depends(get_db)):
    """Send a login OTP by SMS. The response is identical whether or not the phone is registered."""
    await AuthService(db).request_login_otp(req.phone)
    return {"status": "accepted",
            "message": f"If {req.phone[:2]}******{req.phone[-2:]} is registered, an OTP has been sent."}


@router.post("/auth/otp/verify", response_model=AuthTokenResponse)
async def verify_otp(req: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    try:
        user, token, expires_in = await AuthService(db).verify_login_otp(req.phone, req.otp)
    except OtpRejected as exc:
        if exc.too_many_attempts:
            raise HTTPException(status_code=429, detail="Too many attempts. Request a new OTP.")
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    return AuthTokenResponse(access_token=token, expires_in=expires_in, user=_user_out(user))


@router.post("/auth/register/start", status_code=status.HTTP_202_ACCEPTED)
async def start_registration(req: OTPRequest, db: AsyncSession = Depends(get_db)):
    """Step 1: send a code to the phone. The response never reveals whether the number is registered."""
    await RegistrationService(db).start(req.phone)
    return {"status": "accepted", "message": f"A message has been sent to {req.phone[:2]}******{req.phone[-2:]}."}


@router.post("/auth/register/complete", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
async def complete_registration(req: RegistrationComplete, db: AsyncSession = Depends(get_db)):
    """Step 2: the code confirms the phone; the student account is created. No application is submitted."""
    if req.dob >= date.today():
        raise HTTPException(status_code=422, detail="Date of birth must be in the past")
    details = req.model_dump(exclude={"phone", "otp"})
    details["full_name"] = details["full_name"].strip()
    try:
        user, token, expires_in = await RegistrationService(db).complete(req.phone, req.otp, details)
    except RegistrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    return AuthTokenResponse(access_token=token, expires_in=expires_in, user=_user_out(user))


@router.get("/auth/me", response_model=AuthUser)
async def whoami(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.post("/auth/digilocker/callback", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def digilocker_callback():
    """DigiLocker OAuth is not integrated yet."""
    raise HTTPException(status_code=501, detail="DigiLocker login is not implemented in this prototype")


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
