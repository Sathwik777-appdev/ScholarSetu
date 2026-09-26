from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import Reader, StudentPrincipal, officer_covers, officer_or_student, student_principal
from app.ledger.router import actor_of
from app.shared.types import MitraScope, SchemeType
from app.students.models import Student
from .schemas import EligibilityResult, ScholarshipPathway
from .service import EligibilityError, EligibilityService, get_eligibility_service

router = APIRouter(prefix="/v1", tags=["Eligibility & Pathway"])


class EligibilityCheckBody(BaseModel):
    model_config = {"extra": "forbid"}
    scheme: SchemeType
    student_id: Optional[str] = None  # officers only; students always check themselves


def _http(exc: EligibilityError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/eligibility/check", response_model=EligibilityResult)
async def check_eligibility(body: EligibilityCheckBody,
                            reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS)),
                            service: EligibilityService = Depends(get_eligibility_service)):
    """Evaluate the scheme's current decision table on the student's verified facts. Every decision is recorded."""
    if reader.is_officer:
        if not body.student_id:
            raise HTTPException(status_code=422, detail="student_id is required for officer checks")
        student = await service.db.get(Student, body.student_id)
        if student is None or not officer_covers(reader.user, student.state, student.district):
            raise HTTPException(status_code=404, detail="Student not found")
        student_id = body.student_id
    else:
        if body.student_id and body.student_id != reader.student_id:
            raise HTTPException(status_code=403, detail="Students can only check their own eligibility")
        student_id = reader.student_id
    try:
        result = await service.check_eligibility(student_id, body.scheme)
    except EligibilityError as exc:
        raise _http(exc)
    await service.db.commit()
    return result


@router.get("/me/pathway", response_model=ScholarshipPathway)
async def get_pathway(principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
                      service: EligibilityService = Depends(get_eligibility_service)):
    """Where the student is on the scheme ladder and which scheme comes next."""
    try:
        return await service.get_pathway(principal.student_id)
    except EligibilityError as exc:
        raise _http(exc)


@router.post("/me/pathway/prefill", response_model=ScholarshipPathway)
async def prefill_next(principal: StudentPrincipal = Depends(student_principal()),
                       service: EligibilityService = Depends(get_eligibility_service)):
    """Prepare the pre-filled DRAFT for the next rung if verified facts show a transition."""
    try:
        await service.detect_transition(principal.student_id, actor_of(principal.user))
        await service.db.commit()
        return await service.get_pathway(principal.student_id)
    except EligibilityError as exc:
        raise _http(exc)
