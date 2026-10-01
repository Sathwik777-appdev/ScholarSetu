from decimal import Decimal
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.shared.types import CanonicalState, PaymentState, SchemeType, SourceSystem

ACADEMIC_YEAR = r"^20[0-9]{2}-[0-9]{2}$"


class ApplicationCreate(BaseModel):
    # The applicant is always the authenticated student; a student_id in the body is rejected.
    model_config = {"extra": "forbid"}
    scheme: SchemeType
    academic_year: str = Field(..., pattern=ACADEMIC_YEAR)
    details: dict[str, Any] = Field(default_factory=dict)
    # Set to true to proceed after being told you hold another scholarship (one-scheme rule, §6.5).
    acknowledge_one_scheme_rule: bool = False


class ApplicationOut(BaseModel):
    id: str
    student_id: str
    scheme: SchemeType
    academic_year: str
    source_system: SourceSystem
    source_ref: Optional[str]
    canonical_state: CanonicalState
    state_changed_at: datetime
    details: dict[str, Any]
    provisional_flags: list[str] = []
    created_at: datetime


class OfficerApplicationOut(ApplicationOut):
    """An application as an officer sees it inside their jurisdiction."""
    student_name: str
    district: str
    state_name: str
    days_in_state: float


class CountRow(BaseModel):
    key: str
    count: int


class SchemeMoneyRow(BaseModel):
    scheme: SchemeType
    applications: int
    sanctioned: Decimal
    credited: Decimal


class AnalyticsOverview(BaseModel):
    """Totals computed from the ledger for the caller's jurisdiction."""
    scope: str
    total_applications: int
    total_students: int
    by_state: list[CountRow]
    by_scheme: list[SchemeMoneyRow]
    sanctioned_amount: Decimal
    credited_amount: Decimal
    failed_amount: Decimal
    pending_amount: Decimal
    payments_failed: int
    payments_total: int
    open_sla_breaches: int
    open_review_cases: int


class LedgerEventOut(BaseModel):
    event_id: str
    position: int
    application_id: str
    sequence_no: int
    type: str
    source: SourceSystem
    actor: str
    occurred_at: datetime
    payload: dict[str, Any]
    hash_prev: str
    hash: str


class ChainVerification(BaseModel):
    application_id: str
    valid: bool
    events_checked: int
    first_invalid_event_id: Optional[str] = None
    reason: Optional[str] = None


class StudentBrief(BaseModel):
    id: str
    name: str
    dob: date
    household_id: Optional[str]
    district: str


class ApplicationBrief(BaseModel):
    id: str
    scheme: SchemeType
    academic_year: str
    current_state: CanonicalState
    state_since: datetime
    source_system: SourceSystem
    next_action: Optional[str]
    money_received: float


class StudentDashboard(BaseModel):
    student: StudentBrief
    applications: list[ApplicationBrief]
    total_received: float
    current_academic_year: str  # the year a new application is for (server rule, ACADEMIC_YEAR_START_MONTH)


class FamilyDashboard(BaseModel):
    household_id: str
    guardian_name: str
    students: list[StudentDashboard]


class InstalmentOut(BaseModel):
    payment_id: str
    instalment: int
    description: str
    amount: float
    state: PaymentState
    failure_code: Optional[str]
    initiated_at: Optional[datetime]
    credited_at: Optional[datetime]


class ApplicationMoney(BaseModel):
    application_id: str
    scheme: SchemeType
    academic_year: str
    state: CanonicalState
    sanctioned: float
    credited: float
    failed: float
    pending: float
    instalments: list[InstalmentOut]


class MoneyView(BaseModel):
    student_id: str
    total_sanctioned: float
    total_credited: float
    total_failed: float
    total_pending: float
    applications: list[ApplicationMoney]


class PendingAction(BaseModel):
    type: str
    application_id: Optional[str]
    reference_id: str
    description: str
    deadline: Optional[datetime] = None
    action_url: Optional[str] = None


class DeficiencyResponse(BaseModel):
    model_config = {"extra": "forbid"}
    response_text: str = Field(..., min_length=1, max_length=2000)
    document_ids: list[str] = Field(default_factory=list, max_length=10)


class TransitionRequest(BaseModel):
    model_config = {"extra": "forbid"}
    to_state: CanonicalState
    note: str = Field("", max_length=1000)


class RaiseDeficiencyRequest(BaseModel):
    model_config = {"extra": "forbid"}
    code: str = Field(..., pattern=r"^[A-Z0-9_]{3,40}$")
    description: str = Field(..., min_length=5, max_length=1000)
    due_days: int = Field(15, ge=1, le=90)


class SLARow(BaseModel):
    application_id: str
    scheme: SchemeType
    state: CanonicalState
    district: str
    state_name: str
    days_in_state: float
    sla_days: float
    breached: bool


class InstalmentPlan(BaseModel):
    model_config = {"extra": "forbid"}
    description: str = Field(..., min_length=3, max_length=200)
    amount: float = Field(..., gt=0, le=10_000_000)
    # The entitlement this instalment pays, as a path into the scheme's rules file "amounts",
    # e.g. "hosteller_per_year.class_9", "group_1.hosteller_monthly", "tuition_fee".
    component: str = Field(..., min_length=2, max_length=80, pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+)?$")
    months: Optional[int] = Field(None, ge=1, le=12)          # for monthly amounts
    evidence_note: Optional[str] = Field(None, min_length=5, max_length=300)  # for "actual cost" items


class SanctionRequest(BaseModel):
    model_config = {"extra": "forbid"}
    instalments: list[InstalmentPlan] = Field(..., min_length=1, max_length=24)
    note: str = Field("", max_length=1000)
    # One scheme at a time: the scholarship the student gives up for this one (checked against the ledger).
    surrender_application_id: Optional[str] = None
    # Sanctioning outside the rules (not eligible, or above an amount) needs a recorded reason.
    override_reason: Optional[str] = Field(None, min_length=15, max_length=1000)
