from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.dependencies import OFFICER_ROLES, get_current_user, require_role
from app.gateway.models import User
from app.shared.types import ClaimType, ConsentArtefact, UserRole
from app.verification.schemas import ReviewDecisionRequest, VerificationReport
from app.verification.service import VerificationMeshService, get_verification_service

router = APIRouter(prefix="/v1", tags=["Verification Mesh & Review"])


class VerifyClaimsRequest(BaseModel):
    required_claims: list[ClaimType]
    consent_id: str
    # Officers may name the student; students always verify themselves.
    student_id: Optional[str] = None


def _target_student(user: User, requested: Optional[str]) -> str:
    if user.role == UserRole.STUDENT:
        if requested and requested != user.student_id:
            raise HTTPException(status_code=403, detail="Students can only verify their own claims")
        return user.student_id
    if user.role in OFFICER_ROLES:
        if not requested:
            raise HTTPException(status_code=422, detail="student_id is required for officer-initiated verification")
        return requested
    raise HTTPException(status_code=403, detail="Insufficient role")


@router.post("/verify/claims", response_model=VerificationReport)
async def verify_claims(
    request: VerifyClaimsRequest,
    user: User = Depends(get_current_user),
    service: VerificationMeshService = Depends(get_verification_service),
):
    """Trigger multi-source claim verification with attestation reuse and identity matching."""
    student_id = _target_student(user, request.student_id)
    # TODO(Phase 7, S3): replace with a lookup of a stored, unexpired, unrevoked consent.
    consent = ConsentArtefact(
        consent_id=request.consent_id,
        student_id=student_id,
        requester="SCHOLARSETU_VERIFICATION_MESH",
        purpose="MoTA Scholarship Eligibility Verification",
        data_items=[c.value for c in request.required_claims],
        granted_at="2026-09-25T10:00:00Z",
        expires_at="2027-09-25T10:00:00Z"
    )
    return await service.verify_claims(student_id, request.required_claims, consent)


@router.get("/verify/status/{request_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def check_verification_status(request_id: str, user: User = Depends(get_current_user)):
    """Verification runs synchronously today; there is no request tracking to report on."""
    raise HTTPException(status_code=501, detail="Asynchronous verification status is not implemented")


@router.get("/review/cases")
async def get_review_cases(
    sort: str = Query("sla_risk"),
    officer: User = Depends(require_role(*OFFICER_ROLES)),
    service: VerificationMeshService = Depends(get_verification_service),
) -> List[Dict[str, Any]]:
    """Officer review queue sorted by SLA risk."""
    return await service.get_review_cases()


@router.post("/review/cases/{id}/decision")
async def post_review_decision(
    id: str,
    decision: ReviewDecisionRequest,
    officer: User = Depends(require_role(*OFFICER_ROLES)),
    service: VerificationMeshService = Depends(get_verification_service),
):
    """Record officer review decision on a provisional case."""
    result = await service.decide_review_case(id, decision.decision.value, decision.notes, decided_by=officer.id)
    return {
        "status": "success",
        "case_id": id,
        "decision": decision.decision.value,
        "notes": decision.notes,
        "updated_case": result
    }
