"""A student's rights over their personal data (DPDP Act, 2023): see it all, and ask for erasure or correction.

GET  /v1/me/data-export           everything ScholarSetu holds about the student, as JSON (audited)
POST /v1/me/data-requests         ask for erasure or correction (an officer decides; audited)
GET  /v1/me/data-requests         the student's requests and their outcome
GET  /v1/data-requests            officers: open requests in their jurisdiction
POST /v1/data-requests/{id}/resolve   officers: DONE or DECLINED, with the reason the student sees
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    ANALYTICS_ROLES, StudentPrincipal, officer_covers, require_role, scope_to_officer, student_principal,
)
from app.gateway.models import User
from app.gateway.service import record_audit
from app.privacy.models import DataRequest
from app.students.models import Student

router = APIRouter(prefix="/v1", tags=["Data rights"])

MAX_OPEN_REQUESTS = 5
# Never exported: credentials and one-time secrets, even the student's own.
NEVER_EXPORTED = {"otp_hash", "access_token", "code_verifier", "storage_key"}


def _plain(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _rows(objs) -> list[dict]:
    return [{c.name: _plain(getattr(o, c.key)) for c in o.__table__.columns if c.name not in NEVER_EXPORTED}
            for o in objs]


@router.get("/me/data-export")
async def data_export(principal: StudentPrincipal = Depends(student_principal()), db: AsyncSession = Depends(get_db)):
    """Everything ScholarSetu holds about you. Secrets (login code hashes, tokens) are never included."""
    from app.attestation.models import Attestation
    from app.consent.models import Consent
    from app.digilocker.models import DigiLockerSession
    from app.gateway.models import AuditLog
    from app.ledger.models import Application, Deficiency, LedgerEvent, Payment
    from app.nudge.models import Notification
    from app.verification.models import ReviewCase
    from app.wallet.models import WalletDocument

    sid = principal.student_id

    async def all_of(model, *where):
        return _rows((await db.execute(select(model).where(*where))).scalars().all())

    app_ids = select(Application.id).where(Application.student_id == sid)
    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "student": (await all_of(Student, Student.id == sid))[0],
        "accounts": await all_of(User, User.student_id == sid),
        "applications": await all_of(Application, Application.student_id == sid),
        "ledger_events": await all_of(LedgerEvent, LedgerEvent.student_id == sid),
        "payments": await all_of(Payment, Payment.application_id.in_(app_ids)),
        "deficiencies": await all_of(Deficiency, Deficiency.application_id.in_(app_ids)),
        "attestations": await all_of(Attestation, Attestation.student_id == sid),
        "review_cases": await all_of(ReviewCase, ReviewCase.student_id == sid),
        "consents": await all_of(Consent, Consent.student_id == sid),
        "wallet_documents": await all_of(WalletDocument, WalletDocument.student_id == sid),
        "digilocker_sessions": await all_of(DigiLockerSession, DigiLockerSession.student_id == sid),
        "notifications": await all_of(Notification, Notification.student_id == sid),
        "data_requests": await all_of(DataRequest, DataRequest.student_id == sid),
        "access_log": await all_of(AuditLog, AuditLog.student_id == sid),
        "note": "Wallet document files are downloaded one by one from /v1/wallet/documents/{id}/content.",
    }
    await record_audit(db, "DATA_EXPORTED", actor=principal.user, student_id=sid)
    await db.commit()
    return export


class DataRequestIn(BaseModel):
    model_config = {"extra": "forbid"}
    kind: Literal["ERASURE", "CORRECTION"]
    details: str = Field(..., min_length=10, max_length=2000)


class DataRequestOut(BaseModel):
    id: str
    student_id: str
    kind: str
    details: str
    status: str
    resolution: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    student_name: Optional[str] = None
    district: Optional[str] = None


def _out(r: DataRequest, student: Optional[Student] = None) -> DataRequestOut:
    return DataRequestOut(id=r.id, student_id=r.student_id, kind=r.kind, details=r.details, status=r.status,
                          resolution=r.resolution, created_at=r.created_at, resolved_at=r.resolved_at,
                          student_name=student.full_name if student else None,
                          district=student.district if student else None)


@router.post("/me/data-requests", response_model=DataRequestOut, status_code=201)
async def create_data_request(body: DataRequestIn, principal: StudentPrincipal = Depends(student_principal()),
                              db: AsyncSession = Depends(get_db)):
    """Ask for your data to be erased or corrected. An officer decides and the reason is shown to you.
    Records of money paid (the ledger) are kept by law even when erasure is accepted."""
    open_count = await db.scalar(select(func.count()).select_from(DataRequest).where(
        DataRequest.student_id == principal.student_id, DataRequest.status == "OPEN"))
    if open_count >= MAX_OPEN_REQUESTS:
        raise HTTPException(status_code=429, detail="You already have several open requests; wait for a decision")
    request = DataRequest(student_id=principal.student_id, requested_by=principal.user.id, kind=body.kind,
                          details=body.details.strip(), status="OPEN")
    db.add(request)
    await db.flush()
    await record_audit(db, "DATA_REQUEST_CREATED", actor=principal.user, student_id=principal.student_id,
                       details={"data_request_id": request.id, "kind": body.kind})
    await db.commit()
    return _out(request)


@router.get("/me/data-requests", response_model=list[DataRequestOut])
async def my_data_requests(principal: StudentPrincipal = Depends(student_principal()),
                           db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(DataRequest).where(DataRequest.student_id == principal.student_id)
                             .order_by(DataRequest.created_at.desc()))).scalars().all()
    return [_out(r) for r in rows]


@router.get("/data-requests", response_model=list[DataRequestOut])
async def officer_data_requests(status: str = "OPEN", officer: User = Depends(require_role(*ANALYTICS_ROLES)),
                                db: AsyncSession = Depends(get_db)):
    """Data requests from students in the officer's jurisdiction, oldest first."""
    query = scope_to_officer(select(DataRequest, Student).join(Student, Student.id == DataRequest.student_id), officer)
    if status != "ALL":
        query = query.where(DataRequest.status == status)
    rows = (await db.execute(query.order_by(DataRequest.created_at))).all()
    return [_out(r, s) for r, s in rows]


class ResolveIn(BaseModel):
    model_config = {"extra": "forbid"}
    status: Literal["DONE", "DECLINED"]
    resolution: str = Field(..., min_length=10, max_length=2000)


@router.post("/data-requests/{request_id}/resolve", response_model=DataRequestOut)
async def resolve_data_request(request_id: str, body: ResolveIn,
                               officer: User = Depends(require_role(*ANALYTICS_ROLES)),
                               db: AsyncSession = Depends(get_db)):
    request = await db.get(DataRequest, request_id, with_for_update=True)
    student = await db.get(Student, request.student_id) if request else None
    if request is None or not officer_covers(officer, student.state, student.district):
        raise HTTPException(status_code=404, detail="Request not found")
    if request.status != "OPEN":
        raise HTTPException(status_code=409, detail=f"Request already {request.status.lower()}")
    request.status, request.resolution = body.status, body.resolution.strip()
    request.resolved_by, request.resolved_at = officer.id, datetime.now(timezone.utc)
    await record_audit(db, "DATA_REQUEST_RESOLVED", actor=officer, student_id=request.student_id,
                       details={"data_request_id": request.id, "status": body.status})
    await db.commit()
    return _out(request, student)
