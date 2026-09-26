from dataclasses import dataclass
from datetime import date
from typing import Protocol, Optional
from app.shared.types import ClaimType, VerificationMethod, VerificationStatus, ConsentArtefact

@dataclass
class SubjectRef:
    student_id: str
    aadhaar_ref: Optional[str]
    apaar_id: Optional[str]
    name: str
    name_variants: list[str]
    dob: date
    gender: str
    father_name: Optional[str]
    mother_name: Optional[str]
    district: Optional[str]

@dataclass 
class VerificationResult:
    status: VerificationStatus
    confidence: float
    source: str
    method: VerificationMethod
    evidence_hash: Optional[str]
    claim_value: Optional[dict]
    reasons: list[str]
    raw_response: Optional[dict]

class VerifierPlugin(Protocol):
    claim_type: ClaimType
    source_name: str
    priority: int
    
    async def verify(self, subject: SubjectRef, consent: ConsentArtefact) -> VerificationResult:
        ...
    
    async def is_available(self) -> bool:
        ...
