from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import Reader, StudentPrincipal, officer_or_student, student_principal
from app.shared.types import MitraScope, SchemeType
from .schemas import EligibilityResult, ScholarshipPathway
from .service import EligibilityService

router = APIRouter(prefix="/v1", tags=["Eligibility"])


class EligibilityCheckBody(BaseModel):
    scheme: SchemeType
    # Officers may name a student; students always check themselves.
    student_id: Optional[str] = None


def get_eligibility_service() -> EligibilityService:
    return EligibilityService()


@router.post("/eligibility/check", response_model=EligibilityResult)
async def check_eligibility(
    request: EligibilityCheckBody,
    reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS)),
    service: EligibilityService = Depends(get_eligibility_service),
):
    """Check if a student is eligible for a specific scheme."""
    if reader.is_officer:
        if not request.student_id:
            raise HTTPException(status_code=422, detail="student_id is required for officer checks")
        student_id = request.student_id
    else:
        if request.student_id and request.student_id != reader.student_id:
            raise HTTPException(status_code=403, detail="Students can only check their own eligibility")
        student_id = reader.student_id
    return await service.check_eligibility(student_id, request.scheme)


@router.get("/me/pathway", response_model=ScholarshipPathway)
async def get_pathway(
    principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
    service: EligibilityService = Depends(get_eligibility_service),
):
    """Get the student's pathway position and next eligible scheme."""
    return await service.get_pathway(principal.student_id)
