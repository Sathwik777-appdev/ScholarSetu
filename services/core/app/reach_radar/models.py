import uuid
from datetime import datetime, date
from typing import Optional, Any
from sqlalchemy import String, Integer, Float, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

class CoverageAnalysis(Base):
    __tablename__ = "coverage_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    district: Mapped[str] = mapped_column(String, nullable=False)
    block: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    total_enrolled_st: Mapped[int] = mapped_column(Integer, nullable=False)
    total_scholarship_holders: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    scheme_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    pvtg_coverage_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

class OutreachRecord(Base):
    __tablename__ = "outreach_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("coverage_analyses.id"), nullable=False)
    institution_code: Mapped[str] = mapped_column(String, nullable=False)
    institution_name: Mapped[str] = mapped_column(String, nullable=False)
    unreached_count: Mapped[int] = mapped_column(Integer, nullable=False)
    sent_to: Mapped[str] = mapped_column(String, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
