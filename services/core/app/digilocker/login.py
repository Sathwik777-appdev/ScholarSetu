"""Sign in with DigiLocker (the only sign-in for real students; officers use an emailed code).

    POST /v1/auth/digilocker/start     -> DigiLocker's sign-in URL (state + PKCE S256 created here)
    POST /v1/auth/digilocker/complete  {state, code} -> signed in, or a registration token for a new person
    POST /v1/auth/digilocker/register  {registration_token, state, district, ...} -> student account, signed in

The app opens the sign-in URL and DigiLocker sends the person back to DIGILOCKER_LOGIN_REDIRECT_URI (the app's
scholarsetu:// scheme). The app relays the code; the token exchange, with the client secret, happens only here.
Name, date of birth and gender come from DigiLocker and are not typed by the person. The same code works against
the test DigiLocker (mocks/) and the MeriPehchaan sandbox or production: only settings differ.
"""

import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.digilocker.models import DigiLockerLogin
from app.digilocker.router import get_digilocker_http
from app.digilocker.service import TOKEN_PATH, pkce_pair
from app.gateway.models import User
from app.gateway.router import AuthTokenResponse, _user_out
from app.gateway.service import record_audit
from app.shared import places
from app.shared.ids import new_id
from app.shared.ratelimit import limit_code_checks, limit_code_requests
from app.shared.security import create_access_token
from app.shared.types import Gender, UserRole

router = APIRouter(prefix="/v1/auth/digilocker", tags=["Auth & Gateway"])

LOGIN_MINUTES = 15
_GENDERS = {"M": Gender.MALE, "F": Gender.FEMALE, "T": Gender.OTHER, "MALE": Gender.MALE, "FEMALE": Gender.FEMALE}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_dob(value: Optional[str]) -> Optional[date]:
    """DigiLocker sends DDMMYYYY; the test DigiLocker sends ISO dates. Anything else is unknown."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d%m%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _configured() -> None:
    if not (settings.DIGILOCKER_CLIENT_ID and settings.DIGILOCKER_CLIENT_SECRET):
        raise HTTPException(status_code=503, detail="DigiLocker sign-in is not configured on this server")


class StartOut(BaseModel):
    authorize_url: str
    state: str
    redirect_uri: str
    test_service: bool
    label: str


class CompleteIn(BaseModel):
    model_config = {"extra": "forbid"}
    state: str = Field(..., min_length=10, max_length=64)
    code: str = Field(..., min_length=4, max_length=512)


class CompleteOut(BaseModel):
    status: str                                   # SIGNED_IN | NEEDS_SIGNUP
    auth: Optional[AuthTokenResponse] = None
    registration_token: Optional[str] = None
    profile: Optional[dict] = None                # name, dob, gender, as DigiLocker gave them


class RegisterIn(BaseModel):
    model_config = {"extra": "forbid"}
    registration_token: str = Field(..., min_length=20, max_length=64)
    state: str = Field(..., min_length=2, max_length=60)
    district: str = Field(..., min_length=2, max_length=60)
    father_name: Optional[str] = Field(None, max_length=100)
    tribe: Optional[str] = Field(None, max_length=60)
    preferred_language: str = Field("hi", pattern=r"^[a-z]{2,3}$")


def _signed_in(user: User) -> AuthTokenResponse:
    token, expires_in = create_access_token(user.id, user.role.value)
    return AuthTokenResponse(access_token=token, expires_in=expires_in, user=_user_out(user))


@router.post("/start", response_model=StartOut, dependencies=[Depends(limit_code_requests)])
async def start(db: AsyncSession = Depends(get_db)):
    """Begin "Sign in with DigiLocker": returns the page to open in the browser."""
    _configured()
    verifier, challenge = pkce_pair()
    attempt = DigiLockerLogin(state=secrets.token_urlsafe(32), code_verifier=verifier, status="PENDING",
                              expires_at=_now() + timedelta(minutes=LOGIN_MINUTES))
    db.add(attempt)
    await db.commit()
    redirect = settings.DIGILOCKER_LOGIN_REDIRECT_URI
    url = settings.digilocker_authorize_url + "?" + urlencode({
        "response_type": "code", "client_id": settings.DIGILOCKER_CLIENT_ID, "redirect_uri": redirect,
        "state": attempt.state, "code_challenge": challenge, "code_challenge_method": "S256"})
    return StartOut(authorize_url=url, state=attempt.state, redirect_uri=redirect,
                    test_service=settings.digilocker_is_test and settings.DIGILOCKER_MODE == "mock",
                    label="DigiLocker (test)" if settings.DIGILOCKER_MODE == "mock" else "DigiLocker")


@router.post("/complete", response_model=CompleteOut, dependencies=[Depends(limit_code_checks)])
async def complete(body: CompleteIn, db: AsyncSession = Depends(get_db),
                   http: httpx.AsyncClient = Depends(get_digilocker_http)):
    """Exchange DigiLocker's code (server-side, with the PKCE verifier and client secret) and sign the person in."""
    attempt = (await db.execute(select(DigiLockerLogin).where(DigiLockerLogin.state == body.state)
                                .with_for_update())).scalar_one_or_none()
    if attempt is None or attempt.status != "PENDING" or _aware(attempt.expires_at) < _now():
        raise HTTPException(status_code=400, detail="This DigiLocker sign-in has expired or was already used. "
                                                    "Start again.")
    try:
        res = await http.post(TOKEN_PATH, data={
            "grant_type": "authorization_code", "code": body.code, "client_id": settings.DIGILOCKER_CLIENT_ID,
            "client_secret": settings.DIGILOCKER_CLIENT_SECRET, "redirect_uri": settings.DIGILOCKER_LOGIN_REDIRECT_URI,
            "code_verifier": attempt.code_verifier})
    except httpx.TransportError:
        raise HTTPException(status_code=503, detail="DigiLocker could not be reached. Try again.")
    if res.status_code != 200:
        attempt.status, attempt.error = "FAILED", f"token exchange HTTP {res.status_code}"
        await db.commit()
        raise HTTPException(status_code=401, detail="DigiLocker did not confirm the sign-in. Start again.")
    data = res.json()
    digilocker_id = str(data.get("digilockerid") or data.get("sub") or "").strip()
    if not digilocker_id:
        attempt.status, attempt.error = "FAILED", "no DigiLocker id in the token response"
        await db.commit()
        raise HTTPException(status_code=502, detail="DigiLocker did not say who signed in")
    attempt.digilocker_id = digilocker_id
    attempt.profile = {"name": data.get("name"), "dob": data.get("dob"), "gender": data.get("gender")}
    user = (await db.execute(select(User).where(User.digilocker_id == digilocker_id))).scalar_one_or_none()
    if user is not None:
        if not user.is_active:
            attempt.status = "FAILED"
            await db.commit()
            raise HTTPException(status_code=403, detail="This account has been deactivated")
        attempt.status = "DONE"
        await record_audit(db, "LOGIN", actor=user, student_id=user.student_id, details={"via": "digilocker"})
        await db.commit()
        return CompleteOut(status="SIGNED_IN", auth=_signed_in(user))
    attempt.status, attempt.registration_token = "NEEDS_SIGNUP", secrets.token_urlsafe(32)
    await db.commit()
    return CompleteOut(status="NEEDS_SIGNUP", registration_token=attempt.registration_token, profile=attempt.profile)


@router.post("/register", response_model=AuthTokenResponse, status_code=201, dependencies=[Depends(limit_code_checks)])
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    """Create a student account for a person DigiLocker has just confirmed. Name, date of birth and gender come
    from DigiLocker. Registering never submits an application."""
    from app.students.models import Student
    attempt = (await db.execute(select(DigiLockerLogin).where(
        DigiLockerLogin.registration_token == body.registration_token).with_for_update())).scalar_one_or_none()
    if attempt is None or attempt.status != "NEEDS_SIGNUP" or _aware(attempt.expires_at) < _now():
        raise HTTPException(status_code=400, detail="This sign-up has expired. Sign in with DigiLocker again.")
    if await db.scalar(select(User.id).where(User.digilocker_id == attempt.digilocker_id)):
        raise HTTPException(status_code=409, detail="This DigiLocker account already has a ScholarSetu account")
    profile = attempt.profile or {}
    dob = parse_dob(profile.get("dob"))
    gender = _GENDERS.get(str(profile.get("gender") or "").strip().upper())
    name = (profile.get("name") or "").strip()
    if not (name and dob and gender):
        raise HTTPException(status_code=422, detail="DigiLocker did not share your name, date of birth and gender")
    student = Student(id=f"stu-{new_id()}", full_name=" ".join(name.split()).title(), name_variants=[], dob=dob,
                      gender=gender, state=places.tidy(body.state), district=places.tidy(body.district),
                      father_name=body.father_name, tribe=body.tribe, preferred_language=body.preferred_language)
    db.add(student)
    await db.flush()
    user = User(name=student.full_name, role=UserRole.STUDENT, student_id=student.id,
                digilocker_id=attempt.digilocker_id, is_demo=False, is_active=True)
    db.add(user)
    attempt.status, attempt.registration_token = "DONE", None
    await db.flush()
    await record_audit(db, "REGISTERED", actor=user, student_id=student.id, details={"identity_confirmed_by": "DigiLocker"})
    await db.commit()
    return _signed_in(user)
