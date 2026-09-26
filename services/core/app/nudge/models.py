from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Enum as SAEnum, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id
from app.shared.types import NotificationChannel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Notification(Base):
    """One message to one user on one channel. (event_id, user_id, channel) is unique, so a
    redelivered event never notifies twice."""
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    student_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    template_key: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel, name="notification_channel"),
                                                         nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("event_id", "user_id", "channel", name="uq_notification_once"),)
