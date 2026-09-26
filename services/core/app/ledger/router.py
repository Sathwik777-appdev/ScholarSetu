from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import (
    OFFICER_ROLES, Reader, StudentPrincipal, officer_or_student, require_role, student_principal,
)
from app.gateway.models import User
from app.ledger.schemas import (
    ApplicationCreate, ApplicationResponse, DeficiencyResponse, FamilyDashboard, LedgerEventResponse,
    MoneyView, PendingAction, StudentDashboard,
)
from app.ledger.service import LedgerService, get_ledger_service
from app.shared.types import CanonicalState, MitraScope, SourceSystem, UserRole

router = APIRouter(prefix="/v1", tags=["Scholarship Ledger (Student APIs)"])


def _not_found(exc: LookupError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def ensure_application_access(svc: LedgerService, application_id: str, reader: Reader) -> ApplicationResponse:
    """Officers may access any application; students (or their active Mitra) only their own. Others get 404."""
    app = svc.get_application(application_id)
    if app is None or (not reader.is_officer and app.student_id != reader.student_id):
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.get("/me/dashboard", response_model=StudentDashboard)
async def get_dashboard(
    principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
    svc: LedgerService = Depends(get_ledger_service),
):
    try:
        return await svc.get_student_dashboard(principal.student_id)
    except LookupError as exc:
        raise _not_found(exc)


@router.get("/me/household", response_model=FamilyDashboard)
async def get_household(
    user: User = Depends(require_role(UserRole.GUARDIAN)),
    svc: LedgerService = Depends(get_ledger_service),
):
    """Guardian view of every child in the guardian's own household."""
    if not user.household_id:
        raise HTTPException(status_code=404, detail="No household linked to this account")
    try:
        return await svc.get_family_dashboard(user.household_id)
    except LookupError as exc:
        raise _not_found(exc)


@router.get("/applications/{id}/timeline", response_model=list[LedgerEventResponse])
async def get_timeline(
    id: str,
    reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS)),
    svc: LedgerService = Depends(get_ledger_service),
):
    ensure_application_access(svc, id, reader)
    return await svc.get_timeline(id)


@router.get("/me/pending-actions", response_model=list[PendingAction])
async def get_pending_actions(
    principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
    svc: LedgerService = Depends(get_ledger_service),
):
    return await svc.get_pending_actions(principal.student_id)


@router.get("/me/payments", response_model=MoneyView)
async def get_payments(
    principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
    svc: LedgerService = Depends(get_ledger_service),
):
    try:
        return await svc.get_money_view(principal.student_id)
    except LookupError as exc:
        raise _not_found(exc)


@router.post("/applications", response_model=ApplicationResponse)
async def create_application(
    app: ApplicationCreate,
    principal: StudentPrincipal = Depends(student_principal()),
    svc: LedgerService = Depends(get_ledger_service),
):
    """Students apply for themselves; Mitra helpers cannot create applications."""
    # TODO(Phase 4, C4): sequence-based IDs; TODO(Phase 6, C3): one-scheme check before creating.
    response = ApplicationResponse(
        id=f"APP-PM-2026-{principal.student_id[-4:]}",
        student_id=principal.student_id,
        scheme=app.scheme,
        academic_year=app.academic_year,
        canonical_state=CanonicalState.SUBMITTED,
        source_system=SourceSystem.SCHOLARSETU,
        details=app.details
    )
    svc.register_application(response)
    await svc.append_event(
        application_id=response.id,
        event_type="ApplicationSubmitted",
        payload=app.details,
        source=SourceSystem.SCHOLARSETU,
        scheme=app.scheme,
        student_id=principal.student_id
    )
    return response


@router.post("/applications/{id}/deficiencies/{did}/respond")
async def respond_to_deficiency(
    id: str,
    did: str,
    response: DeficiencyResponse,
    principal: StudentPrincipal = Depends(student_principal(MitraScope.RESPOND_DEFICIENCY)),
    svc: LedgerService = Depends(get_ledger_service),
):
    app = ensure_application_access(svc, id, Reader(user=principal.user, student_id=principal.student_id))
    payload = {"deficiency_id": did, "response_text": response.response_text, "docs": response.documents}
    if principal.via_mitra:
        payload["assisted_by_session"] = principal.assist_session.id
    await svc.append_event(
        application_id=id,
        event_type="DeficiencyResolved",
        payload=payload,
        source=SourceSystem.SCHOLARSETU,
        scheme=app.scheme,
        student_id=app.student_id
    )
    return {"status": "recorded", "deficiency_id": did,
            "message": "Response recorded in the ScholarSetu ledger. Forwarding to the source portal is not implemented yet."}


@router.get("/sync", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def sync_events(cursor: str = Query(None), principal: StudentPrincipal = Depends(student_principal())):
    # TODO(Phase 10): delta sync from the persistent event store.
    raise HTTPException(status_code=501, detail="Delta sync is not implemented yet")


@router.post("/sync/outbox", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def sync_outbox(principal: StudentPrincipal = Depends(student_principal())):
    # TODO(Phase 10): idempotent outbox ingestion.
    raise HTTPException(status_code=501, detail="Offline outbox sync is not implemented yet")
