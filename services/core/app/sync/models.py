from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.shared.ids import new_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SyncReceipt(Base):
    """The outcome of one offline action, keyed by the device's idempotency key.

    The receipt is written in the same transaction as the action, so an action is applied at most once
    and a resent action gets back the original outcome."""
    __tablename__ = "sync_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # APPLIED | REJECTED
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_sync_receipt_key"),)
