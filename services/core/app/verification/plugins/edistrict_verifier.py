from app.shared.types import ClaimType, VerificationMethod, VerificationStatus, ConsentArtefact
from app.verification.plugins.base import VerifierPlugin, SubjectRef, VerificationResult

class EDistrictVerifier(VerifierPlugin):
    claim_type: ClaimType = ClaimType.INCOME
    source_name: str = "e-District"
    priority: int = 2
    
    async def verify(self, subject: SubjectRef, consent: ConsentArtefact) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.90,
            source=self.source_name,
            method=VerificationMethod.API,
            evidence_hash="mock_hash_edistrict",
            claim_value={"income": 45000, "tribe_name": "Gond"},
            reasons=["Found valid certificates in e-District portal"],
            raw_response={"income_certificate": "Valid", "caste_certificate": "Valid"}
        )
        
    async def is_available(self) -> bool:
        return True
