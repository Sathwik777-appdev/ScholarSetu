from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import OFFICER_ROLES, Reader, StudentPrincipal, officer_or_student, require_role, student_principal
from app.gateway.models import User
from app.ledger.router import actor_of, ensure_application_access
from app.consent.service import ConsentError, ConsentService
from app.shared.types import MitraScope, ReviewCaseStatus
from app.students.service import StudentNotFound
from app.verification.schemas import (
    InfoResponseRequest, ReviewCaseOut, ReviewDecisionRequest, ReviewDecisionResponse, VerificationReport, VerifyClaimsRequest,
)
from app.verification.plugins.base import source_label
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
    return await service.list_cases(status_filter, officer)


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


@router.post("/review/cases/{case_id}/respond", response_model=ReviewCaseOut)
async def respond_to_info_request(
    case_id: str, body: InfoResponseRequest,
    principal: StudentPrincipal = Depends(student_principal(MitraScope.RESPOND_DEFICIENCY)),
    service: VerificationMeshService = Depends(get_verification_service),
):
    """The student (or a helper they allowed) answers an officer's request for more information. The case goes back
    to the officer's queue with the answer attached."""
    try:
        return await service.respond_info(case_id, principal.student_id, body.response_text.strip(),
                                          actor_of(principal.user),
                                          principal.assist_session.id if principal.via_mitra else None)
    except ReviewCaseError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


CLAIM_LABELS = {
    "IDENTITY": "Your identity (Aadhaar e-KYC)", "ST_STATUS": "Scheduled Tribe certificate",
    "INCOME": "Family income certificate", "DOMICILE": "Domicile certificate",
    "SCHOOL_ENROLMENT": "School enrolment", "HIGHER_ED": "College or university enrolment",
    "ACADEMIC_RECORDS": "Marksheets", "NET_JRF": "UGC-NET / JRF result", "DISABILITY": "Disability certificate",
    "TOP_CLASS_INSTITUTION": "Admission to a top-class institution", "FOREIGN_ADMISSION": "Admission abroad",
}


def _claims_in(node, found: list) -> None:
    """Claim types a decision table reads ("claims.INCOME.annual_income" -> INCOME), in order of appearance."""
    if isinstance(node, dict):
        var = node.get("var")
        if isinstance(var, str) and var.startswith("claims."):
            found.append(var.split(".")[1])
        for v in node.values():
            _claims_in(v, found)
    elif isinstance(node, list):
        for v in node:
            _claims_in(v, found)


@router.get("/applications/{application_id}/verification-plan")
async def verification_plan(application_id: str,
                            reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS)),
                            service: VerificationMeshService = Depends(get_verification_service)):
    """What verifying this application involves: the claims its scheme's rules need, the government sources
    that would be asked about each, and what is already verified. The student consents to exactly this list."""
    from app.attestation.models import Attestation
    from app.eligibility.service import EligibilityError, EligibilityService
    from app.shared.types import AttestationStatus, ClaimType
    from sqlalchemy import select
    app = await ensure_application_access(service.ledger, application_id, reader)
    try:
        table = (await EligibilityService(service.db).rule_version(app.scheme)).decision_table
    except EligibilityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    names: list = ["IDENTITY"]
    _claims_in(table, names)
    claims = [ClaimType(n) for n in dict.fromkeys(names) if n in ClaimType.__members__]
    sources = {c: [source_label(p.source_name) for p in service.verifiers.get(c, [])] for c in claims}
    rows = (await service.db.execute(select(Attestation).where(
        Attestation.student_id == app.student_id, Attestation.claim_type.in_(claims),
        Attestation.status.in_([AttestationStatus.ACTIVE, AttestationStatus.PROVISIONAL]))
        .order_by(Attestation.issued_at))).scalars().all()
    latest = {a.claim_type: a for a in rows}  # last issued wins
    reusable = await service.attestations.find_valid_attestations(app.student_id, claims)
    out = []
    for c in claims:
        att = reusable.get(c) or latest.get(c)
        status = ("VERIFIED" if c in reusable else "PROVISIONAL" if att and att.status == AttestationStatus.PROVISIONAL
                  else "NOT_VERIFIED")
        out.append({"claim_type": c.value, "label": CLAIM_LABELS.get(c.value, c.value.replace("_", " ").title()),
                    "sources": sources[c], "status": status, "verified_by": att.source if att else None,
                    "valid_until": att.valid_until.isoformat() if att and att.valid_until else None,
                    "needs_officer": not sources[c]})
    return {"application_id": app.id, "scheme": app.scheme.value, "claims": out,
            "consent": {"requester": "SCHOLARSETU_VERIFICATION_MESH",
                        "purpose": f"Verify my details for {app.scheme.value.replace('_', ' ').title()} "
                                   f"({app.academic_year})",
                        "data_items": [c.value for c in claims], "duration_days": 30}}
