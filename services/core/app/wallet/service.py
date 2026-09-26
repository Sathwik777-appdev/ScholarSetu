"""Document wallet. Metadata in Postgres; document bytes in object storage (wired in Phase 7)."""

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.wallet.models import WalletDocument
from app.wallet.schemas import WalletDocumentResponse, WalletResponse


def to_response(doc: WalletDocument) -> WalletDocumentResponse:
    return WalletDocumentResponse(
        id=doc.id, student_id=doc.student_id, document_type=doc.document_type, title=doc.title, source=doc.source,
        digilocker_uri=doc.source_ref, content_hash=f"sha256:{doc.content_sha256}", mime_type=doc.mime_type,
        size_bytes=doc.size_bytes, uploaded_at=doc.created_at.isoformat(), verified=doc.issuer_signed,
        metadata_json=doc.metadata_json,
    )


class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_wallet(self, student_id: str) -> WalletResponse:
        docs = list((await self.db.execute(
            select(WalletDocument).where(WalletDocument.student_id == student_id).order_by(WalletDocument.created_at)
        )).scalars())
        return WalletResponse(student_id=student_id, total_documents=len(docs), documents=[to_response(d) for d in docs])


def get_wallet_service(db: AsyncSession = Depends(get_db)) -> WalletService:
    return WalletService(db)
