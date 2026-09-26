from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DbtHealthCheck(Base):
    """One pre-sanction / post-failure check that a payment would reach the student's bank account."""
    __tablename__ = "dbt_health_checks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    application_id: Mapped[str] = mapped_column(String, ForeignKey("applications.id"), index=True, nullable=False)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # PASS | FAIL | UNAVAILABLE
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    bank_account_masked: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    requested_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)


class DbtRetry(Base):
    """A retry of a failed payment after the student says the bank problem is fixed."""
    __tablename__ = "dbt_retries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    payment_id: Mapped[str] = mapped_column(String(36), ForeignKey("payments.id"), index=True, nullable=False)
    application_id: Mapped[str] = mapped_column(String, ForeignKey("applications.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # BLOCKED | SUBMITTED | CREDITED | FAILED
    health_check_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("dbt_health_checks.id"), nullable=True)
    pfms_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    failure_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    requested_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
