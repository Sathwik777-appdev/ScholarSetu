from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Enum as SAEnum, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id
from app.shared.types import ClaimType, ReviewCaseStatus, ReviewDecision, ReviewReason, VerificationStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewCase(Base):
    """A claim routed to an officer instead of being auto-verified (ARCHITECTURE.md §6.4.1, §6.4.5)."""
    __tablename__ = "review_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), index=True, nullable=False)
    application_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    claim_type: Mapped[ClaimType] = mapped_column(SAEnum(ClaimType, name="claim_type"), nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, name="verification_status"), nullable=False)
    reason: Mapped[ReviewReason] = mapped_column(SAEnum(ReviewReason, name="review_reason"), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    identity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # [{source, source_ref, evidence_hash, outcome}] for every source consulted.
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    attestation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("attestations.id"), nullable=True)
    status: Mapped[ReviewCaseStatus] = mapped_column(SAEnum(ReviewCaseStatus, name="review_case_status"),
                                                     index=True, nullable=False)
    decision: Mapped[Optional[ReviewDecision]] = mapped_column(SAEnum(ReviewDecision, name="review_decision"), nullable=True)
    decided_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_event_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sla_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (Index("idx_review_open", "student_id", "application_id", "claim_type", "status"),)
