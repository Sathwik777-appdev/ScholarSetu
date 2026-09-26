from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Optional

from app.shared.types import CanonicalState, SchemeType, SourceSystem, PaymentState

class StudentCreate(BaseModel):
    name: str
    aadhaar_ref: str
    dob: datetime
    household_id: Optional[str] = None

class StudentResponse(BaseModel):
    id: str
    name: str
    aadhaar_ref: str
    dob: datetime
    household_id: Optional[str] = None

class ApplicationCreate(BaseModel):
    # The applicant is always the authenticated student; a student_id in the body is rejected.
    model_config = {"extra": "forbid"}
    scheme: SchemeType
    academic_year: str
    details: dict[str, Any] = Field(default_factory=dict)

class ApplicationResponse(BaseModel):
    id: str
    student_id: str
    scheme: SchemeType
    academic_year: str
    canonical_state: CanonicalState
    source_system: SourceSystem
    details: dict[str, Any]

class ApplicationBrief(BaseModel):
    id: str
    scheme: SchemeType
    academic_year: str
    current_state: CanonicalState
    next_action: Optional[str] = None
    money_received: float = 0.0

class LedgerEventResponse(BaseModel):
    id: str
    application_id: str
    event_type: str
    payload: dict[str, Any]
    source: SourceSystem
    occurred_at: datetime
    event_hash: str

class PendingAction(BaseModel):
    type: str
    description: str
    deadline: Optional[datetime] = None
    action_url: Optional[str] = None

class MoneyView(BaseModel):
    application_id: str
    sanctioned: float
    credited: float
    failed: float
    pending: float
    instalments: list[dict[str, Any]]

class StudentDashboard(BaseModel):
    student: StudentResponse
    applications: list[ApplicationBrief]
    total_received: float

class FamilyDashboard(BaseModel):
    household_id: str
    guardian_name: str
    students: list[StudentDashboard]

class TimelineEntry(BaseModel):
    event_type: str
    occurred_at: datetime
    actor: str
    description: str
    details: dict[str, Any]

class SLAReport(BaseModel):
    total_applications: int
    avg_processing_days: float
    breaches_count: int
    state_durations: dict[str, float]

class DeficiencyResponse(BaseModel):
    response_text: str
    documents: list[str]
