from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import OFFICER_ROLES, Reader, officer_or_student, require_role
from app.gateway.models import User
from app.ledger.router import ensure_application_access
from app.consent.service import ConsentError, ConsentService
from app.shared.types import ReviewCaseStatus
from app.students.service import StudentNotFound
from app.verification.schemas import (
    ReviewCaseOut, ReviewDecisionRequest, ReviewDecisionResponse, VerificationReport, VerifyClaimsRequest,
)
from app.verification.service import ReviewCaseError, VerificationMeshService, get_verification_service

router = APIRouter(prefix="/v1", tags=["Verification Mesh & Review"])


@router.post("/verify/claims", response_model=VerificationReport)
async def verify_claims(
    request: VerifyClaimsRequest,
    reader: Reader = Depends(officer_or_student()),
    service: VerificationMeshService = Depends(get_verification_service),
):
    """Verify the claims an application needs. The student is the application's owner.

    Never reports VERIFIED by default: unconfirmed claims come back PROVISIONAL, MANUAL_REVIEW
    or SOURCE_UNAVAILABLE and are routed to the officer review queue.
    """
    application = await ensure_application_access(service.ledger, request.application_id, reader)
    try:
        consent = await ConsentService(service.db).require(
            request.consent_id, application.student_id, "SCHOLARSETU_VERIFICATION_MESH",
            [c.value for c in request.required_claims])
    except ConsentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    try:
        return await service.verify_claims(application.student_id, application.id, request.required_claims, consent)
    except StudentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/verify/status/{request_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def check_verification_status(request_id: str, user: User = Depends(require_role(*OFFICER_ROLES))):
    """Verification runs synchronously today; there is no request tracking to report on."""
    raise HTTPException(status_code=501, detail="Asynchronous verification status is not implemented")


@router.get("/review/cases", response_model=list[ReviewCaseOut])
async def get_review_cases(
    status_filter: Optional[ReviewCaseStatus] = Query(None, alias="status"),
    sort: str = Query("sla_risk", pattern="^sla_risk$"),
    officer: User = Depends(require_role(*OFFICER_ROLES)),
    service: VerificationMeshService = Depends(get_verification_service),
):
    """Officer review queue, most urgent SLA deadline first."""
    return await service.list_cases(status_filter)


@router.post("/review/cases/{case_id}/decision", response_model=ReviewDecisionResponse)
async def post_review_decision(
    case_id: str,
    body: ReviewDecisionRequest,
    officer: User = Depends(require_role(*OFFICER_ROLES)),
    service: VerificationMeshService = Depends(get_verification_service),
):
    """APPROVE, REJECT or REQUEST_INFO. Writes a ledger event and updates the attestation."""
    try:
        return await service.decide(case_id, body.decision, body.notes, officer, body.claim_value)
    except ReviewCaseError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
