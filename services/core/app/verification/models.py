import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB

from app.database import Base
from app.shared.types import ClaimType, VerificationMethod, ReviewDecision

class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    claim_type: Mapped[ClaimType] = mapped_column(ENUM(ClaimType, name="claim_type_enum", create_type=False), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False) # PENDING, IN_PROGRESS, COMPLETED, FAILED
    source_used: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[VerificationMethod] = mapped_column(ENUM(VerificationMethod, name="verification_method_enum", create_type=False), nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    result_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    evidence_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reasons: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class ReviewCase(Base):
    __tablename__ = "review_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    claim_type: Mapped[ClaimType] = mapped_column(ENUM(ClaimType, name="claim_type_enum", create_type=False), nullable=False)
    evidence_refs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[str] = mapped_column(String, nullable=False)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decision: Mapped[Optional[ReviewDecision]] = mapped_column(ENUM(ReviewDecision, name="review_decision_enum", create_type=False), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sla_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
