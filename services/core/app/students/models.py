"""Student master record: the identity every verification is checked against (ARCHITECTURE.md §7)."""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.types import Gender


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    name_variants: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(SAEnum(Gender, name="gender"), nullable=False)
    father_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mother_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tribe: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pvtg_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    district: Mapped[str] = mapped_column(String, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="hi", nullable=False)
    household_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    # Opaque Aadhaar Data Vault reference; the raw Aadhaar number is never stored.
    aadhaar_ref_token: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    # Needed to query UDISE+/AISHE/APAAR (see ARCHITECTURE.md §19 deviations).
    apaar_id: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    nta_roll_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
