from pydantic import BaseModel
from typing import Optional, Any
from app.shared.types import ClaimType, VerificationStatus

class VerificationRequest(BaseModel):
    student_id: str
    required_claims: list[ClaimType]
    consent_id: str

class ClaimVerificationResult(BaseModel):
    claim_type: ClaimType
    status: VerificationStatus
    confidence: float
    source: str
    evidence_hash: Optional[str]
    claim_value: Optional[dict[str, Any]]
    reasons: list[str]

class VerificationReport(BaseModel):
    student_id: str
    overall_status: VerificationStatus
    claims: list[ClaimVerificationResult]
    identity_resolution_score: Optional[float]
    identity_decision: Optional[str]
    requires_manual_review: bool

class ReviewDecisionRequest(BaseModel):
    decision: VerificationStatus
    notes: str
