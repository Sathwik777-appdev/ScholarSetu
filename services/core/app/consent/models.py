from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Consent(Base):
    """DEPA-style consent artefact (ARCHITECTURE.md §6.9): who may pull what, for which purpose, until when."""
    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"), index=True, nullable=False)
    requester: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    # e.g. ["ST_STATUS", "INCOME"] for verification, ["DIGILOCKER:MARKSHEET_10"] for wallet pulls
    data_items: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    granted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
