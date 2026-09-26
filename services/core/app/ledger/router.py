from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    ANALYTICS_ROLES, OFFICER_ROLES, Reader, StudentPrincipal, officer_covers, officer_or_student, require_role,
    student_principal,
)
from app.gateway.models import User
from app.ledger.models import Application
from app.ledger.schemas import (
    ApplicationCreate, ApplicationOut, ChainVerification, DeficiencyResponse, FamilyDashboard, LedgerEventOut,
    MoneyView, PendingAction, RaiseDeficiencyRequest, SanctionRequest, SLARow, StudentDashboard,
    TransitionRequest,
)
from app.ledger.service import LedgerError, LedgerService, get_ledger_service
from app.shared.types import CanonicalState, MitraScope, SchemeType, UserRole
from app.students.models import Student

router = APIRouter(prefix="/v1", tags=["Scholarship Ledger"])

# Which lifecycle moves each officer role may make by hand (source portals move the rest via adapters).
ROLE_TRANSITIONS: dict[UserRole, set[tuple[CanonicalState, CanonicalState]]] = {
    UserRole.INSTITUTE_OFFICER: {
        (CanonicalState.SUBMITTED, CanonicalState.INSTITUTE_VERIFICATION),
        (CanonicalState.RESUBMITTED, CanonicalState.INSTITUTE_VERIFICATION),
        (CanonicalState.INSTITUTE_VERIFICATION, CanonicalState.AUTHORITY_VERIFICATION),
    },
    UserRole.DISTRICT_OFFICER: {(CanonicalState.AUTHORITY_VERIFICATION, CanonicalState.REJECTED)},
    UserRole.STATE_OFFICER: {(CanonicalState.AUTHORITY_VERIFICATION, CanonicalState.REJECTED)},
}
DEFICIENCY_STAGE = {UserRole.INSTITUTE_OFFICER: CanonicalState.INSTITUTE_VERIFICATION,
                    UserRole.DISTRICT_OFFICER: CanonicalState.AUTHORITY_VERIFICATION,
                    UserRole.STATE_OFFICER: CanonicalState.AUTHORITY_VERIFICATION}


def _http(exc: LedgerError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def actor_of(user: User) -> str:
    return f"user:{user.id}:{user.role.value}"


async def ensure_application_access(ledger: LedgerService, application_id: str, reader: Reader) -> Application:
    """Students (or their active Mitra) see their own applications; officers those in their jurisdiction.
    Everyone else gets 404, so existence is not revealed."""
    app = await ledger.get_application(application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if reader.is_officer:
        student = await ledger.db.get(Student, app.student_id)
        if student is not None and officer_covers(reader.user, student.state, student.district):
            return app
    elif app.student_id == reader.student_id:
        return app
    raise HTTPException(status_code=404, detail="Application not found")


def _app_out(app: Application) -> ApplicationOut:
    return ApplicationOut(id=app.id, student_id=app.student_id, scheme=app.scheme, academic_year=app.academic_year,
                          source_system=app.source_system, source_ref=app.source_ref,
                          canonical_state=app.canonical_state, state_changed_at=app.state_changed_at,
                          details=app.details, created_at=app.created_at)


# ── student views ─────────────────────────────────────────────────────────────


@router.get("/me/dashboard", response_model=StudentDashboard)
async def get_dashboard(principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
                        ledger: LedgerService = Depends(get_ledger_service)):
    try:
        return await ledger.student_dashboard(principal.student_id)
    except LedgerError as exc:
        raise _http(exc)


@router.get("/me/household", response_model=FamilyDashboard)
async def get_household(user: User = Depends(require_role(UserRole.GUARDIAN)),
                        ledger: LedgerService = Depends(get_ledger_service)):
    """Guardian view of every child in the guardian's own household."""
    if not user.household_id:
        raise HTTPException(status_code=404, detail="No household linked to this account")
    try:
        return await ledger.family_dashboard(user.household_id)
    except LedgerError as exc:
        raise _http(exc)


@router.get("/me/payments", response_model=MoneyView)
async def get_payments(principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
                       ledger: LedgerService = Depends(get_ledger_service)):
    return await ledger.money_view(principal.student_id)


@router.get("/me/pending-actions", response_model=list[PendingAction])
async def get_pending_actions(principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
                              ledger: LedgerService = Depends(get_ledger_service)):
    return await ledger.pending_actions(principal.student_id)


@router.post("/applications", response_model=ApplicationOut, status_code=201)
async def create_application(body: ApplicationCreate, principal: StudentPrincipal = Depends(student_principal()),
                             ledger: LedgerService = Depends(get_ledger_service)):
    """Students apply for themselves; Mitra helpers cannot create applications."""
    try:
        app = await ledger.create_application(principal.student_id, body.scheme, body.academic_year,
                                              actor_of(principal.user), body.details)
    except LedgerError as exc:
        raise _http(exc)
    await ledger.db.commit()
    return _app_out(app)


@router.post("/applications/{application_id}/submit", response_model=ApplicationOut)
async def submit_draft(application_id: str, principal: StudentPrincipal = Depends(student_principal()),
                       ledger: LedgerService = Depends(get_ledger_service)):
    """Submit a pre-filled DRAFT application."""
    app = await ensure_application_access(ledger, application_id, Reader(principal.user, principal.student_id))
    try:
        await ledger.transition(app, CanonicalState.SUBMITTED, actor_of(principal.user))
    except LedgerError as exc:
        raise _http(exc)
    await ledger.db.commit()
    return _app_out(app)


@router.post("/applications/{application_id}/deficiencies/{deficiency_id}/respond", response_model=LedgerEventOut)
async def respond_to_deficiency(
    application_id: str, deficiency_id: str, body: DeficiencyResponse,
    principal: StudentPrincipal = Depends(student_principal(MitraScope.RESPOND_DEFICIENCY)),
    ledger: LedgerService = Depends(get_ledger_service),
):
    app = await ensure_application_access(ledger, application_id, Reader(principal.user, principal.student_id))
    response = {"response_text": body.response_text, "document_ids": body.document_ids}
    if principal.via_mitra:
        response["assisted_by_session"] = principal.assist_session.id
    try:
        event = await ledger.respond_deficiency(app, deficiency_id, response, actor_of(principal.user))
    except LedgerError as exc:
        raise _http(exc)
    await ledger.db.commit()
    return LedgerEventOut.model_validate(event, from_attributes=True)


# ── shared (owner or officer) ────────────────────────────────────────────────


@router.get("/applications/{application_id}", response_model=ApplicationOut)
async def get_application(application_id: str,
                          reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS)),
                          ledger: LedgerService = Depends(get_ledger_service)):
    return _app_out(await ensure_application_access(ledger, application_id, reader))


@router.get("/applications/{application_id}/timeline", response_model=list[LedgerEventOut])
async def get_timeline(application_id: str, reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS)),
                       ledger: LedgerService = Depends(get_ledger_service)):
    await ensure_application_access(ledger, application_id, reader)
    return [LedgerEventOut.model_validate(e, from_attributes=True) for e in await ledger.timeline(application_id)]


@router.get("/applications/{application_id}/verify-chain", response_model=ChainVerification)
async def verify_chain(application_id: str, reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS)),
                       ledger: LedgerService = Depends(get_ledger_service)):
    """Recompute the application's hash chain: false means an event was altered, removed or reordered."""
    await ensure_application_access(ledger, application_id, reader)
    check = await ledger.verify_chain(application_id)
    return ChainVerification(**check.__dict__)


# ── officers ─────────────────────────────────────────────────────────────────


@router.get("/applications", response_model=list[ApplicationOut])
async def list_applications(
    state: Optional[CanonicalState] = None, scheme: Optional[SchemeType] = None,
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
    officer: User = Depends(require_role(*OFFICER_ROLES)), db: AsyncSession = Depends(get_db),
):
    """Applications inside the officer's jurisdiction."""
    query = select(Application).join(Student, Student.id == Application.student_id)
    if officer.role != UserRole.MINISTRY:
        query = query.where(Student.state == officer.jurisdiction_state)
        if officer.role in (UserRole.DISTRICT_OFFICER, UserRole.INSTITUTE_OFFICER):
            query = query.where(Student.district == officer.jurisdiction_district)
    if state:
        query = query.where(Application.canonical_state == state)
    if scheme:
        query = query.where(Application.scheme == scheme)
    rows = (await db.execute(query.order_by(Application.state_changed_at).limit(limit).offset(offset))).scalars()
    return [_app_out(a) for a in rows]


@router.post("/officer/applications/{application_id}/transition", response_model=ApplicationOut)
async def officer_transition(application_id: str, body: TransitionRequest,
                             officer: User = Depends(require_role(*OFFICER_ROLES)),
                             ledger: LedgerService = Depends(get_ledger_service)):
    app = await ensure_application_access(ledger, application_id, Reader(officer, None))
    if (app.canonical_state, body.to_state) not in ROLE_TRANSITIONS.get(officer.role, set()):
        raise HTTPException(status_code=403, detail=f"{officer.role.value} cannot move an application from "
                                                    f"{app.canonical_state.value} to {body.to_state.value}")
    try:
        await ledger.transition(app, body.to_state, actor_of(officer), {"note": body.note} if body.note else {})
    except LedgerError as exc:
        raise _http(exc)
    await ledger.db.commit()
    return _app_out(app)


@router.post("/officer/applications/{application_id}/deficiencies", response_model=ApplicationOut)
async def officer_raise_deficiency(application_id: str, body: RaiseDeficiencyRequest,
                                   officer: User = Depends(require_role(*OFFICER_ROLES)),
                                   ledger: LedgerService = Depends(get_ledger_service)):
    app = await ensure_application_access(ledger, application_id, Reader(officer, None))
    if DEFICIENCY_STAGE.get(officer.role) != app.canonical_state:
        raise HTTPException(status_code=403, detail=f"{officer.role.value} cannot raise a deficiency while the "
                                                    f"application is {app.canonical_state.value}")
    try:
        await ledger.raise_deficiency(app, body.code, body.description, officer.role.value, actor_of(officer),
                                      body.due_days)
    except LedgerError as exc:
        raise _http(exc)
    await ledger.db.commit()
    return _app_out(app)


@router.post("/officer/applications/{application_id}/sanction", response_model=ApplicationOut)
async def officer_sanction(application_id: str, body: SanctionRequest,
                           officer: User = Depends(require_role(UserRole.DISTRICT_OFFICER, UserRole.STATE_OFFICER)),
                           ledger: LedgerService = Depends(get_ledger_service)):
    """Sanction with the instalment plan. Amounts are recorded here, once, and read by every other view."""
    app = await ensure_application_access(ledger, application_id, Reader(officer, None))
    try:
        await ledger.sanction(app, [(i.description, Decimal(str(i.amount))) for i in body.instalments],
                              actor_of(officer))
    except LedgerError as exc:
        raise _http(exc)
    await ledger.db.commit()
    return _app_out(app)


@router.get("/analytics/sla", response_model=list[SLARow])
async def sla_monitor(officer: User = Depends(require_role(*ANALYTICS_ROLES)),
                      ledger: LedgerService = Depends(get_ledger_service)):
    """Open applications by time in their current state against the configured SLA."""
    return [row for row in await ledger.sla_monitor()
            if officer_covers(officer, row["state_name"], row["district"])]
