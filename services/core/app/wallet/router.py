from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import Reader, StudentPrincipal, officer_covers, officer_or_student, student_principal
from app.shared.types import MitraScope
from app.students.models import Student
from app.verification.sources import SourceClient, get_source_client
from app.wallet.models import WalletDocument
from app.wallet.schemas import WalletDocumentResponse, WalletResponse
from app.wallet.service import WalletError, WalletService, to_response
from app.wallet.storage import StorageUnavailable, get_object_store

router = APIRouter(prefix="/v1", tags=["Document Wallet"])


class DigiLockerPullRequest(BaseModel):
    model_config = {"extra": "forbid"}
    doc_type: str = Field(..., pattern=r"^[A-Z0-9_]{3,40}$")
    consent_id: str


async def get_wallet_service(db: AsyncSession = Depends(get_db), store=Depends(get_object_store)) -> WalletService:
    return WalletService(db, store)


def _http(exc: WalletError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/me/wallet", response_model=WalletResponse)
async def get_my_wallet(
    principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS, MitraScope.UPLOAD_DOCUMENTS)),
    service: WalletService = Depends(get_wallet_service),
):
    return await service.get_wallet(principal.student_id)


@router.post("/me/wallet/digilocker/pull", response_model=WalletDocumentResponse, status_code=201)
async def pull_from_digilocker(
    body: DigiLockerPullRequest,
    principal: StudentPrincipal = Depends(student_principal(MitraScope.UPLOAD_DOCUMENTS)),
    service: WalletService = Depends(get_wallet_service), sources: SourceClient = Depends(get_source_client),
):
    """Pull an issuer-signed document from DigiLocker. Needs a SCHOLARSETU_WALLET consent for DIGILOCKER:<doc_type>."""
    try:
        doc = await service.pull_from_digilocker(principal.student_id, body.doc_type, body.consent_id,
                                                 principal.user, sources)
    except WalletError as exc:
        raise _http(exc)
    except StorageUnavailable:
        raise HTTPException(status_code=503, detail="Document storage is unavailable; try again later")
    await service.db.commit()
    return to_response(doc)


@router.post("/me/wallet/documents", response_model=WalletDocumentResponse, status_code=201)
async def upload_document(
    document_type: str = Form(..., pattern=r"^[A-Z0-9_]{3,40}$"), title: str = Form(..., min_length=3, max_length=120),
    file: UploadFile = File(...),
    response: Response = None,
    idempotency_key: Optional[str] = Header(None, min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_\-:.]+$"),
    principal: StudentPrincipal = Depends(student_principal(MitraScope.UPLOAD_DOCUMENTS)),
    service: WalletService = Depends(get_wallet_service),
):
    """Upload a PDF, JPEG or PNG (the content is checked, not the file name).

    An upload queued offline sends an Idempotency-Key: resending it returns the first upload (200) instead of
    storing the document twice."""
    from sqlalchemy.exc import IntegrityError
    from app.sync.models import SyncReceipt
    from app.sync.router import _receipt

    user_id = principal.user.id
    if idempotency_key:
        existing = await _receipt(service.db, user_id, idempotency_key)
        if existing is not None:
            if existing.status != "APPLIED" or not existing.result:
                raise HTTPException(status_code=existing.http_status, detail=existing.error)
            response.status_code = 200
            return WalletDocumentResponse(**existing.result)
    data = await file.read(settings.WALLET_MAX_UPLOAD_BYTES + 1)
    try:
        doc = await service.upload(principal.student_id, document_type, title, data, principal.user,
                                   settings.WALLET_MAX_UPLOAD_BYTES)
    except WalletError as exc:
        raise _http(exc)
    except StorageUnavailable:
        raise HTTPException(status_code=503, detail="Document storage is unavailable; try again later")
    out = to_response(doc)
    if idempotency_key:
        service.db.add(SyncReceipt(user_id=user_id, idempotency_key=idempotency_key, action="UPLOAD_DOCUMENT",
                                   status="APPLIED", http_status=201, result=out.model_dump(mode="json")))
    try:
        await service.db.commit()
    except IntegrityError:  # the same upload arrived twice at once; the first one wins
        await service.db.rollback()
        existing = await _receipt(service.db, user_id, idempotency_key)
        response.status_code = 200
        return WalletDocumentResponse(**existing.result)
    return out


@router.get("/wallet/documents/{document_id}/content")
async def read_document(document_id: str,
                        reader: Reader = Depends(officer_or_student(MitraScope.VIEW_STATUS, MitraScope.UPLOAD_DOCUMENTS)),
                        service: WalletService = Depends(get_wallet_service)):
    """The document bytes, for the owner (or their active Mitra) and officers in the student's jurisdiction."""
    doc = await service.db.get(WalletDocument, document_id)
    allowed = doc is not None and (doc.student_id == reader.student_id if not reader.is_officer else False)
    if doc is not None and reader.is_officer:
        student = await service.db.get(Student, doc.student_id)
        allowed = officer_covers(reader.user, student.state, student.district)
    if not allowed:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        data = await service.read(doc, reader.user)
    except WalletError as exc:
        raise _http(exc)
    except StorageUnavailable:
        raise HTTPException(status_code=503, detail="Document storage is unavailable; try again later")
    await service.db.commit()
    return Response(content=data, media_type=doc.mime_type,
                    headers={"Content-Disposition": f'inline; filename="{doc.document_type.lower()}"'})
