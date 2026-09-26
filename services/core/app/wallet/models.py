from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WalletDocument(Base):
    """Metadata for a document in the student's wallet; the bytes live in object storage."""
    __tablename__ = "wallet_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), index=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)          # DIGILOCKER | UPLOAD
    source_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # DigiLocker document id
    issuer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    issuer_signed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
