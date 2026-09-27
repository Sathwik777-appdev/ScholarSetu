from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    ANALYTICS_ROLES, OFFICER_ROLES, Reader, StudentPrincipal, officer_covers, officer_or_student, require_role,
    student_principal,
)
from app.gateway.models import User
from app.ledger.models import Application
from app.ledger.schemas import (
    AnalyticsOverview, ApplicationCreate, ApplicationOut, ChainVerification, CountRow, OfficerApplicationOut,
    SchemeMoneyRow, DeficiencyResponse, FamilyDashboard, LedgerEventOut,
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


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _app_out(app: Application) -> ApplicationOut:
    return ApplicationOut(id=app.id, student_id=app.student_id, scheme=app.scheme, academic_year=app.academic_year,
                          source_system=app.source_system, source_ref=app.source_ref,
                          canonical_state=app.canonical_state, state_changed_at=app.state_changed_at,
                          details=app.details, provisional_flags=app.provisional_flags or [],
                          created_at=app.created_at)


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
    """Students apply for themselves; Mitra helpers cannot create applications.

    One scholarship at a time (ARCHITECTURE.md §6.5): a duplicate for the same scheme and year is refused;
    holding a different scheme returns 409 with the rule explained, and the student may proceed by
    resending with acknowledge_one_scheme_rule=true (the application is then flagged).
    """
    from app.eligibility.service import EligibilityService
    check = await EligibilityService(ledger.db).check_one_scheme_rule(principal.student_id, body.scheme,
                                                                      body.academic_year)
    if check.blocking or (check.has_conflict and not body.acknowledge_one_scheme_rule):
        raise HTTPException(status_code=409, detail={"code": "ONE_SCHEME_RULE", "message": check.message,
                                                     "current_holding": check.current_holding,
                                                     "holding_application_id": check.holding_application_id,
                                                     "can_acknowledge": not check.blocking})
    try:
        app = await ledger.create_application(principal.student_id, body.scheme, body.academic_year,
                                              actor_of(principal.user), body.details)
    except LedgerError as exc:
        raise _http(exc)
    if check.has_conflict:
        app.provisional_flags = [f"MUST_SURRENDER:{check.holding_application_id}"]
        await ledger.append_event(app, "OneSchemeRuleAcknowledged",
                                  {"holding_application_id": check.holding_application_id,
                                   "message": check.message}, actor_of(principal.user))
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


def _scope(query, officer: User):
    """Restrict a query joined to Student to the officer's jurisdiction."""
    if officer.role != UserRole.MINISTRY:
        query = query.where(Student.state == officer.jurisdiction_state)
        if officer.role in (UserRole.DISTRICT_OFFICER, UserRole.INSTITUTE_OFFICER):
            query = query.where(Student.district == officer.jurisdiction_district)
    return query


@router.get("/applications", response_model=list[OfficerApplicationOut])
async def list_applications(
    state: Optional[CanonicalState] = None, scheme: Optional[SchemeType] = None,
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
    officer: User = Depends(require_role(*OFFICER_ROLES)), db: AsyncSession = Depends(get_db),
):
    """Applications inside the officer's jurisdiction."""
    query = _scope(select(Application, Student).join(Student, Student.id == Application.student_id), officer)
    if state:
        query = query.where(Application.canonical_state == state)
    if scheme:
        query = query.where(Application.scheme == scheme)
    now = datetime.now(timezone.utc)
    rows = (await db.execute(query.order_by(Application.state_changed_at).limit(limit).offset(offset))).all()
    return [OfficerApplicationOut(**_app_out(a).model_dump(), student_name=s.full_name, district=s.district,
                                  state_name=s.state,
                                  days_in_state=round((now - _utc(a.state_changed_at)).total_seconds() / 86400, 1))
            for a, s in rows]


@router.get("/analytics/overview", response_model=AnalyticsOverview)
async def analytics_overview(officer: User = Depends(require_role(*ANALYTICS_ROLES)),
                             ledger: LedgerService = Depends(get_ledger_service)):
    """Application and payment totals for the caller's jurisdiction, computed from the ledger tables."""
    from app.ledger.models import Payment
    from app.verification.models import ReviewCase
    from app.shared.types import PaymentState
    from app.verification.service import OPEN_CASE_STATUSES
    db = ledger.db
    apps = _scope(select(Application.id, Application.scheme, Application.canonical_state, Application.student_id)
                  .join(Student, Student.id == Application.student_id), officer).subquery()
    by_state = (await db.execute(select(apps.c.canonical_state, func.count()).group_by(apps.c.canonical_state))).all()
    scheme_counts = dict((await db.execute(select(apps.c.scheme, func.count()).group_by(apps.c.scheme))).all())
    money = (await db.execute(select(apps.c.scheme, Payment.state, func.count(), func.sum(Payment.amount))
                              .join(Payment, Payment.application_id == apps.c.id)
                              .group_by(apps.c.scheme, Payment.state))).all()
    zero = Decimal("0")
    per_scheme: dict = {k: {"sanctioned": zero, "credited": zero} for k in scheme_counts}
    totals = {"failed": zero, "pending": zero}
    payments_total = payments_failed = 0
    for scheme, pstate, n, amount in money:
        amount = amount or zero
        payments_total += n
        per_scheme.setdefault(scheme, {"sanctioned": zero, "credited": zero})["sanctioned"] += amount
        if pstate == PaymentState.CREDITED:
            per_scheme[scheme]["credited"] += amount
        elif pstate == PaymentState.FAILED:
            totals["failed"] += amount
            payments_failed += n
        else:
            totals["pending"] += amount
    open_cases = await db.scalar(_scope(select(func.count()).select_from(ReviewCase)
                                        .join(Student, Student.id == ReviewCase.student_id), officer)
                                 .where(ReviewCase.status.in_(list(OPEN_CASE_STATUSES))))
    breaches = sum(1 for row in await ledger.sla_monitor()
                   if row["breached"] and officer_covers(officer, row["state_name"], row["district"]))
    scope = ("All India" if officer.role == UserRole.MINISTRY else
             officer.jurisdiction_state if officer.role == UserRole.STATE_OFFICER else
             f"{officer.jurisdiction_district}, {officer.jurisdiction_state}")
    return AnalyticsOverview(
        scope=scope,
        total_applications=sum(n for _, n in by_state),
        total_students=await db.scalar(select(func.count(func.distinct(apps.c.student_id)))) or 0,
        by_state=[CountRow(key=s.value, count=n) for s, n in sorted(by_state, key=lambda r: -r[1])],
        by_scheme=[SchemeMoneyRow(scheme=k, applications=scheme_counts.get(k, 0), **v) for k, v in per_scheme.items()],
        sanctioned_amount=sum((v["sanctioned"] for v in per_scheme.values()), zero),
        credited_amount=sum((v["credited"] for v in per_scheme.values()), zero),
        failed_amount=totals["failed"], pending_amount=totals["pending"],
        payments_failed=payments_failed, payments_total=payments_total,
        open_sla_breaches=breaches, open_review_cases=open_cases or 0)


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
