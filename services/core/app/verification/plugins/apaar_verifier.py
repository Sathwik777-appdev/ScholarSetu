from app.shared.types import ClaimType, VerificationMethod, VerificationStatus, ConsentArtefact
from app.verification.plugins.base import VerifierPlugin, SubjectRef, VerificationResult

class APAARVerifier(VerifierPlugin):
    claim_type: ClaimType = ClaimType.ACADEMIC_RECORDS
    source_name: str = "APAAR"
    priority: int = 1
    
    async def verify(self, subject: SubjectRef, consent: ConsentArtefact) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.98,
            source=self.source_name,
            method=VerificationMethod.API,
            evidence_hash="mock_hash_apaar",
            claim_value={"apaar_id": subject.apaar_id, "academic_credits": 120},
            reasons=["Found valid academic records via APAAR ID"],
            raw_response={"credits": 120, "status": "Active"}
        )
        
    async def is_available(self) -> bool:
        return True
