import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

class DBTHealthCheck(Base):
    __tablename__ = "dbt_health_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False)
    aadhaar_seeded: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    account_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    name_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    account_type_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    overall_status: Mapped[str] = mapped_column(String, nullable=False) # HEALTHY, ISSUES_FOUND, CHECK_FAILED
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class DBTRetry(Base):
    __tablename__ = "dbt_retries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    failure_code: Mapped[str] = mapped_column(String, nullable=False)
    plain_message: Mapped[str] = mapped_column(String, nullable=False)
    fix_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_initiated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[Optional[str]] = mapped_column(String, nullable=True) # SUCCESS, FAILED_AGAIN
