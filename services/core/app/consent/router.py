from typing import List

from fastapi import APIRouter, Depends

from app.dependencies import StudentPrincipal, student_principal
from .schemas import ConsentCreate, ConsentResponse
from .service import ConsentService

router = APIRouter(prefix="/v1", tags=["Consent"])

# Consent is personal: only the student (never a Mitra helper) can list, grant or revoke it.


def get_consent_service() -> ConsentService:
    return ConsentService()


@router.get("/me/consents", response_model=List[ConsentResponse])
async def list_consents(principal: StudentPrincipal = Depends(student_principal()),
                        service: ConsentService = Depends(get_consent_service)):
    """List all consents for the authenticated student."""
    return await service.list_consents(principal.student_id)


@router.post("/consents", response_model=ConsentResponse)
async def create_consent(request: ConsentCreate, principal: StudentPrincipal = Depends(student_principal()),
                         service: ConsentService = Depends(get_consent_service)):
    """Grant a new consent."""
    return await service.create_consent(
        student_id=principal.student_id,
        requester=request.requester,
        data_items=request.data_items,
        purpose=request.purpose,
        duration_days=request.duration_days
    )


@router.delete("/consents/{consent_id}")
async def revoke_consent(consent_id: str, principal: StudentPrincipal = Depends(student_principal()),
                         service: ConsentService = Depends(get_consent_service)):
    """Revoke a consent. TODO(Phase 7, S3): persist consents; 404 for unknown ids."""
    await service.revoke_consent(consent_id, principal.student_id)
    return {"status": "revoked"}
