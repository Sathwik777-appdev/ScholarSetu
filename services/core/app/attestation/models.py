from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id
from app.shared.types import AttestationStatus, ClaimType, VerificationMethod


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Attestation(Base):
    __tablename__ = "attestations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), nullable=False)
    claim_type: Mapped[ClaimType] = mapped_column(SAEnum(ClaimType, name="claim_type"), nullable=False)
    claim_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[VerificationMethod] = mapped_column(SAEnum(VerificationMethod, name="verification_method"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AttestationStatus] = mapped_column(SAEnum(AttestationStatus, name="attestation_status"), nullable=False)
    # Issued from the test government services (see Settings.SOURCES_ARE_TEST): never to be read as the real source.
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    # Compact JWS (EdDSA) over the full attestation; re-signed on every status change.
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (Index("idx_attest_student_claim_status", "student_id", "claim_type", "status"),)
