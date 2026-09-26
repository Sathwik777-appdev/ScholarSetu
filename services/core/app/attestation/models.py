import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB

from app.database import Base
from app.shared.types import ClaimType, VerificationMethod, AttestationStatus

class Attestation(Base):
    __tablename__ = "attestations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    claim_type: Mapped[ClaimType] = mapped_column(ENUM(ClaimType, name="claim_type_enum", create_type=False), nullable=False)
    claim_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[VerificationMethod] = mapped_column(ENUM(VerificationMethod, name="verification_method_enum", create_type=False), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AttestationStatus] = mapped_column(ENUM(AttestationStatus, name="attestation_status_enum", create_type=False), nullable=False)
    signature: Mapped[str] = mapped_column(String, nullable=False)
    verification_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("verification_requests.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_attest_student_claim_status", "student_id", "claim_type", "status"),
    )
