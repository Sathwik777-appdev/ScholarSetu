from app.shared.types import ClaimType, VerificationMethod, VerificationStatus, ConsentArtefact
from app.verification.plugins.base import VerifierPlugin, SubjectRef, VerificationResult

class UDISEVerifier(VerifierPlugin):
    claim_type: ClaimType = ClaimType.SCHOOL_ENROLMENT
    source_name: str = "UDISE+"
    priority: int = 2
    
    async def verify(self, subject: SubjectRef, consent: ConsentArtefact) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.92,
            source=self.source_name,
            method=VerificationMethod.API,
            evidence_hash="mock_hash_udise",
            claim_value={"school_name": "Test High School", "udise_code": "27340000000"},
            reasons=["Found active enrollment in UDISE+"],
            raw_response={"status": "Enrolled"}
        )
        
    async def is_available(self) -> bool:
        return True
