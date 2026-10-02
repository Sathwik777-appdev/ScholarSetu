from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from app.shared.types import ClaimType

class AttestationBrief(BaseModel):
    attestation_id: str
    claim_type: ClaimType
    issue_date: datetime
    expiry_date: Optional[datetime]
    status: str

class AttestationResponse(BaseModel):
    attestation_id: str
    student_id: str
    claim_type: ClaimType
    claim_value: dict[str, Any]
    source: str
    method: str
    confidence: float
    evidence_hash: Optional[str]
    issue_date: datetime
    expiry_date: Optional[datetime]
    signature: str  # compact JWS (EdDSA) over the full attestation; see AttestationService.signed_payload
    status: str

class ScholarshipPassport(BaseModel):
    student_id: str
    attestations: dict[ClaimType, list[AttestationResponse]]

class AttestationVerification(BaseModel):
    is_valid: bool
    reason: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
