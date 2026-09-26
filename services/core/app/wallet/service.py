"""Document wallet (ARCHITECTURE.md §6.1): DigiLocker pulls and student uploads. Bytes in object storage,
metadata in Postgres. Every pull needs the student's consent; every read is audit-logged."""

import hashlib
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consent.service import ConsentError, ConsentService
from app.gateway.models import User
from app.gateway.service import record_audit
from app.shared.ids import new_id
from app.students.models import Student
from app.verification.sources import SourceClient, SourceUnavailable
from app.wallet.models import WalletDocument
from app.wallet.schemas import WalletDocumentResponse, WalletResponse
from app.wallet.storage import ObjectStore

# (magic bytes, mime type) — the declared content type is never trusted.
SIGNATURES = [(b"%PDF-", "application/pdf"), (b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG\r\n\x1a\n", "image/png")]


class WalletError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def sniff_mime(data: bytes) -> Optional[str]:
    return next((mime for magic, mime in SIGNATURES if data.startswith(magic)), None)


def to_response(doc: WalletDocument) -> WalletDocumentResponse:
    return WalletDocumentResponse(
        id=doc.id, student_id=doc.student_id, document_type=doc.document_type, title=doc.title, source=doc.source,
        digilocker_uri=doc.source_ref, content_hash=f"sha256:{doc.content_sha256}", mime_type=doc.mime_type,
        size_bytes=doc.size_bytes, uploaded_at=doc.created_at.isoformat(), verified=doc.issuer_signed,
        metadata_json=doc.metadata_json,
    )


class WalletService:
    def __init__(self, db: AsyncSession, store: ObjectStore):
        self.db = db
        self.store = store

    async def get_wallet(self, student_id: str) -> WalletResponse:
        docs = list((await self.db.execute(
            select(WalletDocument).where(WalletDocument.student_id == student_id).order_by(WalletDocument.created_at)
        )).scalars())
        return WalletResponse(student_id=student_id, total_documents=len(docs), documents=[to_response(d) for d in docs])

    async def _store(self, student_id: str, data: bytes, mime: str, **fields) -> WalletDocument:
        doc_id = new_id()
        key = f"students/{student_id}/{doc_id}"
        await self.store.put(key, data, mime)
        doc = WalletDocument(id=doc_id, student_id=student_id, storage_key=key, mime_type=mime, size_bytes=len(data),
                             content_sha256=hashlib.sha256(data).hexdigest(), **fields)
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def pull_from_digilocker(self, student_id: str, doc_type: str, consent_id: str, actor: User,
                                   sources: SourceClient) -> WalletDocument:
        try:
            await ConsentService(self.db).require(consent_id, student_id, "SCHOLARSETU_WALLET", [f"DIGILOCKER:{doc_type}"])
        except ConsentError as exc:
            raise WalletError(exc.status_code, exc.detail)
        student = await self.db.get(Student, student_id)
        try:
            meta = await sources.request("GET", f"/digilocker/issued/{student.aadhaar_ref_token}",
                                         params={"doc_type": doc_type})
            if meta is None:
                raise WalletError(404, f"No issued {doc_type} in the student's DigiLocker")
            existing = (await self.db.execute(select(WalletDocument).where(
                WalletDocument.student_id == student_id, WalletDocument.source_ref == meta["doc_id"]))).scalar_one_or_none()
            if existing is not None:
                return existing
            data = await sources.request_bytes("GET", f"/digilocker/issued/{student.aadhaar_ref_token}/file",
                                               params={"doc_type": doc_type})
        except SourceUnavailable:
            raise WalletError(503, "DigiLocker could not be reached; try again later")
        mime = sniff_mime(data or b"")
        if mime is None:
            raise WalletError(502, "DigiLocker returned a file that is not a PDF or image")
        doc = await self._store(student_id, data, mime, document_type=doc_type,
                                title=f"{doc_type.replace('_', ' ').title()} ({meta.get('issuer', 'DigiLocker')})",
                                source="DIGILOCKER", source_ref=meta["doc_id"], issuer=meta.get("issuer"),
                                issuer_signed=True, uploaded_by=actor.id,
                                metadata_json={"holder_name": meta.get("holder_name"), "consent_id": consent_id})
        await record_audit(self.db, "WALLET_DIGILOCKER_PULL", actor=actor, student_id=student_id,
                           details={"document_id": doc.id, "doc_type": doc_type, "consent_id": consent_id})
        return doc

    async def upload(self, student_id: str, document_type: str, title: str, data: bytes, actor: User,
                     max_bytes: int) -> WalletDocument:
        if not data:
            raise WalletError(422, "The file is empty")
        if len(data) > max_bytes:
            raise WalletError(413, f"The file is larger than {max_bytes // (1024 * 1024)} MB")
        mime = sniff_mime(data)
        if mime is None:
            raise WalletError(415, "Only PDF, JPEG or PNG files are accepted")
        doc = await self._store(student_id, data, mime, document_type=document_type, title=title, source="UPLOAD",
                                issuer=None, issuer_signed=False, uploaded_by=actor.id, metadata_json={})
        await record_audit(self.db, "WALLET_UPLOAD", actor=actor, student_id=student_id,
                           details={"document_id": doc.id, "document_type": document_type, "bytes": len(data)})
        return doc

    async def read(self, doc: WalletDocument, actor: User) -> bytes:
        data = await self.store.get(doc.storage_key)
        if hashlib.sha256(data).hexdigest() != doc.content_sha256:
            raise WalletError(500, "Stored document failed its integrity check")
        await record_audit(self.db, "WALLET_DOCUMENT_READ", actor=actor, student_id=doc.student_id,
                           details={"document_id": doc.id})
        return data
