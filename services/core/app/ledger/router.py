from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    ANALYTICS_ROLES, OFFICER_ROLES, Reader, StudentPrincipal, officer_covers, officer_or_student, require_role,
    scope_to_officer, student_principal,
)
from app.gateway.models import User
from app.gateway.service import record_audit
from app.ledger.models import Application
from app.ledger.schemas import (
    AnalyticsOverview, ApplicationCreate, ApplicationOut, ChainVerification, CountRow, OfficerApplicationOut,
    SchemeMoneyRow, DeficiencyResponse, FamilyDashboard, LedgerEventOut,
    MoneyView, PendingAction, RaiseDeficiencyRequest, SanctionRequest, SLARow, StudentDashboard,
    TransitionRequest,
)
from app.ledger.service import LedgerError, LedgerService, get_ledger_service
from app.shared import places
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


async def _possible_duplicate(db: AsyncSession, student_id: str, academic_year: str, exclude: str) -> Optional[str]:
    """Another student record with the same name, date of birth and district that already applied this
    year: most likely the same person registered twice (e.g. with a second phone number)."""
    me = await db.get(Student, student_id)
    return (await db.execute(
        select(Application.id).join(Student, Student.id == Application.student_id).where(
            Student.id != student_id, Student.dob == me.dob,
            places.sql_key(Student.full_name) == places.key(me.full_name),
            places.sql_key(Student.district) == places.key(me.district),
            Application.academic_year == academic_year, Application.id != exclude,
            Application.canonical_state.notin_([CanonicalState.REJECTED, CanonicalState.SURRENDERED,
                                                CanonicalState.DRAFT])).limit(1))).scalar_one_or_none()


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
    flags = []
    duplicate = await _possible_duplicate(ledger.db, principal.student_id, body.academic_year, app.id)
    if duplicate:
        flags.append(f"POSSIBLE_DUPLICATE_OF:{duplicate}")  # blocks sanction until an officer decides
    if check.has_conflict:
        flags.append(f"MUST_SURRENDER:{check.holding_application_id}")
    app.provisional_flags = flags
    if check.has_conflict:
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
    if body.document_ids:  # only documents from this student's own wallet may be attached
        from app.wallet.models import WalletDocument
        owned = set((await ledger.db.execute(select(WalletDocument.id).where(
            WalletDocument.id.in_(body.document_ids), WalletDocument.student_id == app.student_id))).scalars())
        unknown = [d for d in body.document_ids if d not in owned]
        if unknown:
            raise HTTPException(status_code=422, detail=f"Not documents in your wallet: {', '.join(unknown)}")
    response = {"response_text": body.response_text, "document_ids": list(dict.fromkeys(body.document_ids))}
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
    return scope_to_officer(query, officer)


@router.get("/applications", response_model=list[OfficerApplicationOut])
async def list_applications(
    state: Optional[CanonicalState] = None, scheme: Optional[SchemeType] = None,
    q: Optional[str] = Query(None, max_length=80, description="Student name or application ID (part of either)"),
    open_only: bool = Query(False, description="Leave out finished applications (credited, rejected, surrendered)"),
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
    officer: User = Depends(require_role(*OFFICER_ROLES)), db: AsyncSession = Depends(get_db),
):
    """Applications inside the officer's jurisdiction, longest in their stage first."""
    query = _scope(select(Application, Student).join(Student, Student.id == Application.student_id), officer)
    if state:
        query = query.where(Application.canonical_state == state)
    if scheme:
        query = query.where(Application.scheme == scheme)
    if open_only:
        query = query.where(Application.canonical_state.notin_(
            [CanonicalState.CREDITED, CanonicalState.REJECTED, CanonicalState.SURRENDERED]))
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.where(func.lower(Student.full_name).like(like) | func.lower(Application.id).like(like))
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
    breaches = sum(1 for row in await ledger.sla_monitor(lambda q: _scope(q, officer)) if row["breached"])
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
    await ledger.lock(app)  # role and stage checks below must see the committed state
    if (app.canonical_state, body.to_state) not in ROLE_TRANSITIONS.get(officer.role, set()):
        raise HTTPException(status_code=403, detail=f"{officer.role.value} cannot move an application from "
                                                    f"{app.canonical_state.value} to {body.to_state.value}")
    if body.to_state == CanonicalState.REJECTED and len(body.note.strip()) < 10:
        raise HTTPException(status_code=422, detail="Say why the application is rejected (a note of at least "
                                                    "10 characters); the student sees it")
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
    await ledger.lock(app)  # role and stage checks below must see the committed state
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
    """Sanction with the instalment plan. Amounts are recorded here, once, and read by every other view.

    Refused (409) while a review case is open or while the student holds another scholarship that is
    not surrendered in this same step. Not eligible under the current rules, or an amount outside the
    rules, is refused (422) unless the officer gives an override reason, which the ledger records."""
    from app.eligibility.service import EligibilityError, EligibilityService
    from app.ledger.sanction_policy import check_instalments
    from app.verification.models import ReviewCase
    from app.verification.service import OPEN_CASE_STATUSES

    app = await ensure_application_access(ledger, application_id, Reader(officer, None))
    await ledger.lock(app)  # role and stage checks below must see the committed state
    if app.canonical_state != CanonicalState.AUTHORITY_VERIFICATION:
        raise HTTPException(status_code=409, detail=f"Only applications in authority verification can be "
                                                    f"sanctioned (this one is {app.canonical_state.value})")
    db = ledger.db
    open_cases = (await db.execute(select(ReviewCase.id, ReviewCase.claim_type).where(
        ReviewCase.application_id == app.id, ReviewCase.status.in_(list(OPEN_CASE_STATUSES))))).all()
    if open_cases:
        raise HTTPException(status_code=409, detail={
            "code": "OPEN_REVIEW_CASES",
            "message": "Decide the open review cases first: " + ", ".join(c.claim_type.value for c in open_cases),
            "review_case_ids": [c.id for c in open_cases]})

    eligibility = EligibilityService(db)
    actor = actor_of(officer)
    # One scheme at a time: another scholarship held this year must be surrendered in this same step.
    held = [h for h in await eligibility.active_holdings(app.student_id, app.academic_year) if h.id != app.id]
    if held and body.surrender_application_id != held[0].id:
        raise HTTPException(status_code=409, detail={
            "code": "ONE_SCHEME_RULE",
            "message": f"The student holds {held[0].scheme.value} ({held[0].id}) for {app.academic_year}. "
                       f"Resend with surrender_application_id={held[0].id} to surrender it with this sanction.",
            "holding_application_id": held[0].id})
    if body.surrender_application_id and not held:
        raise HTTPException(status_code=422, detail="There is no other scholarship to surrender")
    try:
        if held:
            await ledger.surrender(held[0], f"Surrendered for {app.scheme.value} ({app.id})", actor, app.id)
        result = await eligibility.check_eligibility(app.student_id, app.scheme, record=True)
        version = await eligibility.rule_version(app.scheme)
    except EligibilityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except LedgerError as exc:
        raise _http(exc)

    violations = [] if result.eligible else [f"Not eligible under rules {result.rule_version}: "
                                             + " ".join(result.reasons)]
    violations += check_instalments(version.decision_table.get("amounts", {}), body.instalments)
    violations += [f"Possible duplicate registration of the same student: {f.split(':', 1)[1]}"
                   for f in (app.provisional_flags or []) if f.startswith("POSSIBLE_DUPLICATE_OF:")]
    if violations and not body.override_reason:
        raise HTTPException(status_code=422, detail={
            "code": "OUTSIDE_RULES", "message": "This sanction is outside the scheme rules.",
            "violations": violations,
            "how_to_proceed": "Correct the plan, or resend with override_reason explaining why."})
    record = {
        "rule_version": result.rule_version, "eligibility_decision_id": result.decision_id,
        "eligibility_status": result.status,
        "components": [{"instalment": n, "component": i.component, "months": i.months,
                        "evidence_note": i.evidence_note} for n, i in enumerate(body.instalments, start=1)],
    }
    if violations:
        record["override"] = {"reason": body.override_reason, "violations": violations, "by": actor}
    if body.note:
        record["note"] = body.note
    try:
        await ledger.sanction(app, [(i.description, Decimal(str(i.amount))) for i in body.instalments],
                              actor, record=record)
    except LedgerError as exc:
        raise _http(exc)
    await record_audit(db, "SANCTIONED_WITH_OVERRIDE" if violations else "SANCTIONED", actor=officer,
                       student_id=app.student_id, details={"application_id": app.id, "violations": violations})
    await db.commit()
    return _app_out(app)


@router.get("/analytics/sla", response_model=list[SLARow])
async def sla_monitor(officer: User = Depends(require_role(*ANALYTICS_ROLES)),
                      ledger: LedgerService = Depends(get_ledger_service)):
    """Open applications by time in their current state against the configured SLA."""
    return await ledger.sla_monitor(lambda q: _scope(q, officer))


# ── officer workbench helpers ────────────────────────────────────────────────


@router.get("/officer/applications/{application_id}/sanction-options")
async def sanction_options(application_id: str,
                           officer: User = Depends(require_role(UserRole.DISTRICT_OFFICER, UserRole.STATE_OFFICER)),
                           ledger: LedgerService = Depends(get_ledger_service)):
    """What a sanction can pay under the scheme's current rules, and any scholarship the student must give up.

    Each component is one `component` value for an instalment: fixed (a cap), monthly (rate x months) or
    actual cost (needs an evidence note). The same rules check the sanction itself."""
    from app.eligibility.service import EligibilityError, EligibilityService
    app = await ensure_application_access(ledger, application_id, Reader(officer, None))
    eligibility = EligibilityService(ledger.db)
    try:
        version = await eligibility.rule_version(app.scheme)
    except EligibilityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    components = []
    for key, item in version.decision_table.get("amounts", {}).items():
        value, unit = item.get("value"), str(item.get("unit", ""))
        for path, v in ([(f"{key}.{k}", v) for k, v in value.items()] if isinstance(value, dict) else [(key, value)]):
            kind = ("monthly" if "month" in unit.lower() else "fixed") if isinstance(v, (int, float)) else "actual"
            components.append({"component": path, "label": item.get("label") or humanize_key(path), "kind": kind,
                               "amount": v if isinstance(v, (int, float)) else None, "unit": unit,
                               "note": None if kind != "actual" else str(v),
                               "verified_by_team": bool(item.get("verified_by_team")), "source": item.get("source")})
    held = [h for h in await eligibility.active_holdings(app.student_id, app.academic_year) if h.id != app.id]
    return {"application_id": app.id, "scheme": app.scheme.value, "rule_version": version.version,
            "state": app.canonical_state.value, "components": components,
            "must_surrender": [{"application_id": h.id, "scheme": h.scheme.value} for h in held],
            "flags": app.provisional_flags or []}


def humanize_key(path: str) -> str:
    return path.replace(".", " · ").replace("_", " ").capitalize()


@router.get("/officer/applications/{application_id}/documents")
async def application_documents(application_id: str, officer: User = Depends(require_role(*OFFICER_ROLES)),
                                ledger: LedgerService = Depends(get_ledger_service)):
    """The documents in the student's wallet (metadata only; open one with /v1/wallet/documents/{id}/content).
    Every listing is audited."""
    from app.wallet.models import WalletDocument
    from app.wallet.service import to_response
    app = await ensure_application_access(ledger, application_id, Reader(officer, None))
    docs = (await ledger.db.execute(select(WalletDocument).where(WalletDocument.student_id == app.student_id)
                                    .order_by(WalletDocument.created_at))).scalars().all()
    await record_audit(ledger.db, "OFFICER_LISTED_WALLET", actor=officer, student_id=app.student_id,
                       details={"application_id": app.id, "documents": len(docs)})
    await ledger.db.commit()
    return [to_response(d).model_dump(mode="json") for d in docs]
