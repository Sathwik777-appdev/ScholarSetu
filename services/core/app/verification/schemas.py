from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.shared.types import ClaimType, ReviewCaseStatus, ReviewDecision, ReviewReason, VerificationStatus


class VerifyClaimsRequest(BaseModel):
    model_config = {"extra": "forbid"}
    application_id: str
    required_claims: list[ClaimType] = Field(..., min_length=1)
    consent_id: str


class SourceOutcome(BaseModel):
    source: str
    status: VerificationStatus
    source_ref: Optional[str] = None
    evidence_hash: Optional[str] = None
    reasons: list[str] = Field(default_factory=list)


class ClaimVerificationResult(BaseModel):
    claim_type: ClaimType
    status: VerificationStatus
    confidence: float
    source: Optional[str]
    evidence_hash: Optional[str]
    claim_value: Optional[dict[str, Any]]
    reasons: list[str]
    identity_decision: Optional[str] = None
    identity_score: Optional[float] = None
    attestation_id: Optional[str] = None
    attestation_status: Optional[str] = None
    review_case_id: Optional[str] = None
    sources_consulted: list[SourceOutcome] = Field(default_factory=list)


class VerificationReport(BaseModel):
    student_id: str
    application_id: str
    overall_status: VerificationStatus
    claims: list[ClaimVerificationResult]
    requires_manual_review: bool
    review_case_ids: list[str]


class ReviewDecisionRequest(BaseModel):
    model_config = {"extra": "forbid"}
    decision: ReviewDecision
    notes: str = Field(..., min_length=3)
    # Required only to APPROVE a case where no source returned a value to attest.
    claim_value: Optional[dict[str, Any]] = None


class ReviewCaseOut(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = None
    application_id: str
    claim_type: ClaimType
    verification_status: VerificationStatus
    reason: ReviewReason
    explanation: str
    identity_score: Optional[float]
    evidence_refs: list[dict[str, Any]]
    attestation_id: Optional[str]
    status: ReviewCaseStatus
    decision: Optional[ReviewDecision]
    decided_by: Optional[str]
    decided_at: Optional[datetime]
    notes: Optional[str]
    decision_event_id: Optional[str]
    sla_deadline: datetime
    created_at: datetime


class ReviewDecisionResponse(BaseModel):
    case: ReviewCaseOut
    ledger_event_id: str
    attestation_id: Optional[str]
    attestation_status: Optional[str]
