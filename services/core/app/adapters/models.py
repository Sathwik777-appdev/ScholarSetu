from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Enum as SAEnum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id
from app.shared.types import SourceSystem


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ParkedEvent(Base):
    """A portal status the adapter could not map or apply. Never guessed; an officer resolves it."""
    __tablename__ = "parked_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_system: Mapped[SourceSystem] = mapped_column(SAEnum(SourceSystem, name="source_system"), nullable=False)
    source_ref: Mapped[str] = mapped_column(String, index=True, nullable=False)
    raw_status: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    application_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
