from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional, Protocol

from app.shared.types import ClaimType, ConsentArtefact, VerificationMethod, VerificationStatus
from app.verification.identity_resolver import IdentityRecord
from app.verification.sources import SourceClient


@dataclass
class SubjectRef:
    """The student as recorded in ScholarSetu; every source's answer is checked against this."""
    student_id: str
    aadhaar_ref: Optional[str]
    apaar_id: Optional[str]
    nta_roll_number: Optional[str]
    name: str
    name_variants: list[str]
    dob: date
    gender: str
    father_name: Optional[str]
    mother_name: Optional[str]
    district: Optional[str]


@dataclass
class VerificationResult:
    """What one source said about one claim.

    status is VERIFIED when the source confirms the claim (the mesh still checks that the
    holder identity matches), MANUAL_REVIEW when it answered but did not confirm, and
    SOURCE_UNAVAILABLE when it could not be reached.
    """
    status: VerificationStatus
    source: str
    method: VerificationMethod = VerificationMethod.API
    confidence: float = 0.0
    evidence_hash: Optional[str] = None
    source_ref: Optional[str] = None
    claim_value: Optional[dict[str, Any]] = None
    subject_record: Optional[IdentityRecord] = None
    reasons: list[str] = field(default_factory=list)


class VerifierPlugin(Protocol):
    claim_types: tuple[ClaimType, ...]
    source_name: str
    priority: int

    async def verify(self, claim_type: ClaimType, subject: SubjectRef, consent: ConsentArtefact,
                     client: SourceClient) -> VerificationResult:
        ...


def not_confirmed(source: str, reason: str, body: Optional[dict] = None) -> VerificationResult:
    from app.verification.sources import evidence_hash
    return VerificationResult(status=VerificationStatus.MANUAL_REVIEW, source=source, reasons=[reason],
                              evidence_hash=evidence_hash(body) if body else None)


def parse_date(value: Optional[str]) -> Optional[date]:
    return date.fromisoformat(value) if value else None
