from pydantic import BaseModel, Field
from typing import List, Optional
from app.shared.types import PaymentState

class DBTIssue(BaseModel):
    code: str
    message: str
    message_hi: str
    fix_steps: List[str]

class DBTHealthCheckResult(BaseModel):
    overall_status: str
    checks: List[str] = Field(default_factory=list)
    issues: List[DBTIssue] = Field(default_factory=list)

class DBTFailureGuidance(BaseModel):
    failure_code: str
    plain_message: str
    plain_message_hi: str
    fix_steps: List[str]
    retry_id: str

class DBTRetryResult(BaseModel):
    retry_initiated: bool
    message: str

class DBTStatus(BaseModel):
    health_check: DBTHealthCheckResult
    payment_state: PaymentState
    retries: List[str] = Field(default_factory=list)
