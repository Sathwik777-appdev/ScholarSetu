from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.ledger.schemas import ApplicationOut, LedgerEventOut


class SyncPage(BaseModel):
    events: list[LedgerEventOut]
    applications: list[ApplicationOut]   # current state of every application the events touch
    next_cursor: int                     # send this back as ?cursor= next time
    has_more: bool
    server_time: datetime


class OutboxAction(str, Enum):
    CREATE_APPLICATION = "CREATE_APPLICATION"
    SUBMIT_APPLICATION = "SUBMIT_APPLICATION"
    RESPOND_DEFICIENCY = "RESPOND_DEFICIENCY"
    MARK_NOTIFICATION_READ = "MARK_NOTIFICATION_READ"


class OutboxItem(BaseModel):
    model_config = {"extra": "forbid"}
    idempotency_key: str = Field(..., min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_\-:.]+$")
    action: OutboxAction
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None  # when the student acted, on the device (informational)


class OutboxBatch(BaseModel):
    model_config = {"extra": "forbid"}
    items: list[OutboxItem] = Field(..., min_length=1, max_length=50)


class ItemStatus(str, Enum):
    APPLIED = "APPLIED"      # done now
    DUPLICATE = "DUPLICATE"  # done before under this key; `result`/`error` are the original outcome
    REJECTED = "REJECTED"    # refused for good (validation, permission, conflict): tell the student, do not resend
    RETRY = "RETRY"          # temporary server problem: keep it in the outbox and resend later


class OutboxItemResult(BaseModel):
    idempotency_key: str
    action: OutboxAction
    status: ItemStatus
    original_status: Optional[ItemStatus] = None  # for DUPLICATE: APPLIED or REJECTED
    http_status: int
    result: Optional[dict[str, Any]] = None
    error: Optional[Any] = None


class OutboxResponse(BaseModel):
    results: list[OutboxItemResult]
