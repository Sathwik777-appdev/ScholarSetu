from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

from app.attestation.schemas import AttestationVerification, ScholarshipPassport
from app.attestation.keys import get_signer
from app.attestation.service import AttestationService, get_attestation_service
from app.dependencies import OFFICER_ROLES, StudentPrincipal, get_current_user, student_principal
from app.gateway.models import User
from app.shared.types import MitraScope

router = APIRouter(prefix="/v1", tags=["Scholarship Passport & Attestations"])


class JwsVerifyRequest(BaseModel):
    jws: str


@router.get("/me/attestations", response_model=ScholarshipPassport)
async def get_my_passport(
    principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
    service: AttestationService = Depends(get_attestation_service),
):
    """The student's Scholarship Passport: all attestations, each with its compact JWS in `signature`."""
    return await service.get_passport(principal.student_id)


@router.get("/attestations/public-key")
async def get_public_key():
    """Public verification key (JWK set) so anyone can verify an attestation JWS offline."""
    return {"keys": [get_signer().jwk]}


@router.post("/attestations/verify-jws", response_model=AttestationVerification)
async def verify_presented_jws(
    req: JwsVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify an attestation JWS a student presents (signature, status and expiry)."""
    service = AttestationService(db=db, signer=get_signer())
    ver = service.verify_jws(req.jws)
    if ver.is_valid and ver.payload:
        sub = ver.payload.get("subject")
        if sub:
            from app.students.models import Student
            student = await db.get(Student, sub)
            if student:
                ver.student_name = student.full_name
                ver.guardian_name = student.father_name
    return ver


@router.get("/attestations/{attestation_id}/verify", response_model=AttestationVerification)
async def verify_attestation(
    attestation_id: str,
    user: User = Depends(get_current_user),
    service: AttestationService = Depends(get_attestation_service),
):
    """Verify a stored attestation. Only its owner or an officer may ask."""
    att = await service.get(attestation_id)
    if att is None or (user.student_id != att.student_id and user.role not in OFFICER_ROLES):
        raise HTTPException(status_code=404, detail="Attestation not found")
    return await service.verify_attestation(attestation_id)
