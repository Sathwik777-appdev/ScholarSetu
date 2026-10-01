"""Scholarship Ledger tables (ARCHITECTURE.md §6.3, §7): the append-only event log is the history;
applications, deficiencies and payments are its current-state rows, written in the same transaction."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    JSON, BigInteger, DateTime, Enum as SAEnum, ForeignKey, Identity, Index, Integer, Numeric, Sequence, String, Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.types import CanonicalState, PaymentState, SchemeType, SourceSystem

APPLICATION_SEQ = Sequence("application_seq", start=1)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Household(Base):
    __tablename__ = "households"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    guardian_name: Mapped[str] = mapped_column(String, nullable=False)
    guardian_phone: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


OPEN_APPLICATION_SQL = "canonical_state NOT IN ('REJECTED', 'SURRENDERED')"


class Application(Base):
    __tablename__ = "applications"

    # APP-{SCHEME_CODE}-{YEAR}-{zero-padded seq}, e.g. APP-PM-2026-000812
    id: Mapped[str] = mapped_column(String, primary_key=True)
    seq: Mapped[int] = mapped_column(BigInteger, APPLICATION_SEQ, unique=True, nullable=False)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), index=True, nullable=False)
    scheme: Mapped[SchemeType] = mapped_column(SAEnum(SchemeType, name="scheme_type"), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(7), nullable=False)
    source_system: Mapped[SourceSystem] = mapped_column(SAEnum(SourceSystem, name="source_system"), nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    canonical_state: Mapped[CanonicalState] = mapped_column(SAEnum(CanonicalState, name="canonical_state"),
                                                            index=True, nullable=False)
    state_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    provisional_flags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("source_system", "source_ref", name="uq_application_source_ref"),
        Index("idx_app_scheme_year", "scheme", "academic_year"),
        # One open application per student, scheme and year, enforced by the database: application-level
        # checks alone let two simultaneous submissions both through. Closed applications do not count.
        Index("uq_application_open_per_scheme_year", "student_id", "scheme", "academic_year", unique=True,
              postgresql_where=text(OPEN_APPLICATION_SQL)),
    )


class LedgerEvent(Base):
    """Append-only, hash-chained per application. Never updated or deleted by the application."""
    __tablename__ = "ledger_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Global, monotonically increasing position: the cursor for offline delta sync.
    position: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True, nullable=False)
    application_id: Mapped[str] = mapped_column(String, ForeignKey("applications.id"), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    scheme: Mapped[SchemeType] = mapped_column(SAEnum(SchemeType, name="scheme_type"), nullable=False)
    source: Mapped[SourceSystem] = mapped_column(SAEnum(SourceSystem, name="source_system"), nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)  # "user:<id>:<ROLE>", "system:<component>", "source:<NSP>"
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    hash_prev: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (UniqueConstraint("application_id", "sequence_no", name="uq_ledger_app_seq"),)


class Deficiency(Base):
    __tablename__ = "deficiencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(String, ForeignKey("applications.id"), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    raised_by_role: Mapped[str] = mapped_column(String, nullable=False)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    response: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    application_id: Mapped[str] = mapped_column(String, ForeignKey("applications.id"), index=True, nullable=False)
    instalment: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    state: Mapped[PaymentState] = mapped_column(SAEnum(PaymentState, name="payment_state"), nullable=False)
    failure_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pfms_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    initiated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    credited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (UniqueConstraint("application_id", "instalment", name="uq_payment_instalment"),)


class OutboxMessage(Base):
    """Transactional outbox: rows are written with the change and published to NATS after commit."""
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)  # NATS dedupe id
    subject: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
