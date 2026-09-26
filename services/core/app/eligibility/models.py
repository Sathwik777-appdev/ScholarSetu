from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id
from app.shared.types import SchemeType


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RuleVersion(Base):
    """A scheme's decision table as loaded from rules/*.json. Content is immutable per (scheme, version)."""
    __tablename__ = "rule_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scheme: Mapped[SchemeType] = mapped_column(SAEnum(SchemeType, name="scheme_type"), nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_table: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (UniqueConstraint("scheme", "version", "effective_from", name="uq_rule_version"),)


class EligibilityDecision(Base):
    """Every eligibility decision, with the rule version and the facts it was made on."""
    __tablename__ = "eligibility_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), index=True, nullable=False)
    scheme: Mapped[SchemeType] = mapped_column(SAEnum(SchemeType, name="scheme_type"), nullable=False)
    rule_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("rule_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    missing: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    facts: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
