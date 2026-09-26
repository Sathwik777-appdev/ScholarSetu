from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.shared.types import PaymentState


class DBTCheck(BaseModel):
    code: str
    status: str   # PASS | FAIL | UNAVAILABLE
    detail: str


class DBTIssue(BaseModel):
    code: str
    message: str
    message_hi: str
    fix_steps: list[str]
    fix_steps_hi: list[str]


class DBTHealthCheckResult(BaseModel):
    id: str
    application_id: str
    overall_status: str
    checks: list[DBTCheck]
    issues: list[DBTIssue]
    bank_account_masked: Optional[str]
    checked_at: datetime


class PaymentWithGuidance(BaseModel):
    payment_id: str
    instalment: int
    amount: float
    state: PaymentState
    failure_code: Optional[str]
    guidance: Optional[DBTIssue]


class DBTRetryOut(BaseModel):
    id: str
    payment_id: str
    status: str
    pfms_ref: Optional[str]
    failure_code: Optional[str]
    issues: list[DBTIssue] = Field(default_factory=list)
    created_at: datetime


class DBTStatus(BaseModel):
    application_id: str
    latest_health_check: Optional[DBTHealthCheckResult]
    payments: list[PaymentWithGuidance]
    retries: list[DBTRetryOut]


class RetryRequest(BaseModel):
    model_config = {"extra": "forbid"}
    confirm_fixed: bool = Field(..., description="The student confirms the bank problem has been fixed")
