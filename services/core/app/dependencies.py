"""Common FastAPI dependencies: DB session, authentication, roles, Mitra acting principals, service tokens."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.gateway.models import AssistSession, User
from app.gateway.service import record_audit
from app.shared.security import decode_access_token, service_token_matches
from app.shared.types import AssistSessionStatus, MitraScope, UserRole

OFFICER_ROLES = (UserRole.INSTITUTE_OFFICER, UserRole.DISTRICT_OFFICER, UserRole.STATE_OFFICER, UserRole.MINISTRY)
ANALYTICS_ROLES = (UserRole.DISTRICT_OFFICER, UserRole.STATE_OFFICER, UserRole.MINISTRY)

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


async def get_db_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    return session


async def _user_from_token(token: str, db: AsyncSession) -> User:
    try:
        claims = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid or expired token")
    user = await db.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token")
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticated user loaded from the users table. The role always comes from the DB row."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    return await _user_from_token(credentials.credentials, db)


def require_role(*roles: UserRole):
    async def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user
    return _dep


@dataclass
class StudentPrincipal:
    """Who is acting, and for which student. Mitra helpers act through an ACTIVE assist session."""
    user: User
    student_id: str
    assist_session: Optional[AssistSession] = None

    @property
    def via_mitra(self) -> bool:
        return self.assist_session is not None


async def _resolve_student_principal(request: Request, user: User, db: AsyncSession,
                                     x_mitra_session: Optional[str],
                                     mitra_scopes: tuple[MitraScope, ...]) -> StudentPrincipal:
    if user.role == UserRole.STUDENT:
        if not user.student_id:
            raise HTTPException(status_code=403, detail="Student account is not linked to a student record")
        return StudentPrincipal(user=user, student_id=user.student_id)

    if user.role == UserRole.MITRA:
        if not mitra_scopes:
            raise HTTPException(status_code=403, detail="This action cannot be performed in Mitra mode")
        if not x_mitra_session:
            raise HTTPException(status_code=403, detail="X-Mitra-Session header required")
        session = await db.get(AssistSession, x_mitra_session)
        if session is None or session.mitra_user_id != user.id:
            raise HTTPException(status_code=403, detail="Unknown assist session")
        if session.status != AssistSessionStatus.ACTIVE:
            raise HTTPException(status_code=403, detail=f"Assist session is {session.status.value}")
        expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="Assist session has expired")
        if session.scope not in mitra_scopes:
            raise HTTPException(status_code=403,
                                detail=f"Assist session scope {session.scope.value} does not allow this action")
        await record_audit(db, "MITRA_ACTION", actor=user, student_id=session.student_id,
                           assist_session_id=session.id,
                           details={"method": request.method, "path": request.url.path})
        await db.commit()
        return StudentPrincipal(user=user, student_id=session.student_id, assist_session=session)

    raise HTTPException(status_code=403, detail="Only students (or an authorised Mitra) can access this")


def student_principal(*mitra_scopes: MitraScope):
    """Resolve the student a request acts for.

    - STUDENT users act for themselves.
    - MITRA users must send X-Mitra-Session naming an ACTIVE, unexpired session they own
      whose scope is one of `mitra_scopes`. Every such action is audit-logged.
    - Everyone else is refused.
    """
    async def _dep(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        x_mitra_session: Optional[str] = Header(None),
    ) -> StudentPrincipal:
        return await _resolve_student_principal(request, user, db, x_mitra_session, mitra_scopes)
    return _dep


def officer_covers(user: User, student_state: Optional[str], student_district: Optional[str]) -> bool:
    """Whether an officer's jurisdiction includes a student's state/district."""
    if user.role == UserRole.MINISTRY:
        return True
    if user.role == UserRole.STATE_OFFICER:
        return bool(user.jurisdiction_state) and user.jurisdiction_state == student_state
    if user.role in (UserRole.DISTRICT_OFFICER, UserRole.INSTITUTE_OFFICER):
        return (bool(user.jurisdiction_district) and user.jurisdiction_state == student_state
                and user.jurisdiction_district == student_district)
    return False


@dataclass
class Reader:
    """An officer (any student's records) or a student principal (own records only)."""
    user: User
    student_id: Optional[str]  # None for officers

    @property
    def is_officer(self) -> bool:
        return self.student_id is None


def officer_or_student(*mitra_scopes: MitraScope):
    async def _dep(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        x_mitra_session: Optional[str] = Header(None),
    ) -> Reader:
        if user.role in OFFICER_ROLES:
            return Reader(user=user, student_id=None)
        principal = await _resolve_student_principal(request, user, db, x_mitra_session, mitra_scopes)
        return Reader(user=user, student_id=principal.student_id)
    return _dep


async def require_skill_service(x_service_token: Optional[str] = Header(None)) -> None:
    """JAGO server-to-server auth: a shared secret for the prototype (mTLS in production)."""
    from app.config import settings
    if not settings.SKILL_SERVICE_TOKEN:
        raise HTTPException(status_code=503, detail="JAGO skill endpoint is not configured")
    if not service_token_matches(x_service_token):
        raise _unauthorized("Invalid service token")


async def get_skill_student(
    x_student_session: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_skill_service),
) -> User:
    """The student JAGO acts for, taken only from the student's own access token (authenticated in JAGO's channel)."""
    if not x_student_session:
        raise _unauthorized("X-Student-Session header required")
    user = await _user_from_token(x_student_session, db)
    if user.role != UserRole.STUDENT or not user.student_id:
        raise HTTPException(status_code=403, detail="Student session required")
    return user

