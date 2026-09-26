from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import StudentPrincipal, student_principal
from .schemas import ConsentCreate, ConsentResponse
from .service import ConsentError, ConsentService, to_response

router = APIRouter(prefix="/v1", tags=["Consent"])

# Consent is personal: only the student (never a Mitra helper) can list, grant or revoke it.


@router.get("/me/consents", response_model=list[ConsentResponse])
async def list_consents(principal: StudentPrincipal = Depends(student_principal()), db: AsyncSession = Depends(get_db)):
    return [to_response(c) for c in await ConsentService(db).list_for(principal.student_id)]


@router.post("/consents", response_model=ConsentResponse, status_code=201)
async def grant_consent(body: ConsentCreate, principal: StudentPrincipal = Depends(student_principal()),
                        db: AsyncSession = Depends(get_db)):
    consent = await ConsentService(db).grant(principal.student_id, body.requester, body.purpose, body.data_items,
                                             body.duration_days, principal.user)
    await db.commit()
    return to_response(consent)


@router.delete("/consents/{consent_id}", response_model=ConsentResponse)
async def revoke_consent(consent_id: str, principal: StudentPrincipal = Depends(student_principal()),
                         db: AsyncSession = Depends(get_db)):
    try:
        consent = await ConsentService(db).revoke(consent_id, principal.student_id, principal.user)
    except ConsentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    await db.commit()
    return to_response(consent)
