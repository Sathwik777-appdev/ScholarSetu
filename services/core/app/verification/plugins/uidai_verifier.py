from app.shared.types import ClaimType, VerificationMethod, VerificationStatus, ConsentArtefact
from app.verification.plugins.base import VerifierPlugin, SubjectRef, VerificationResult

class UIDAIeKYCVerifier(VerifierPlugin):
    claim_type: ClaimType = ClaimType.IDENTITY
    source_name: str = "UIDAI"
    priority: int = 1
    
    async def verify(self, subject: SubjectRef, consent: ConsentArtefact) -> VerificationResult:
        # Mock UIDAI API call
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.99,
            source=self.source_name,
            method=VerificationMethod.API,
            evidence_hash="mock_hash_uidai",
            claim_value={"name": subject.name, "dob": str(subject.dob), "gender": subject.gender, "address": "123 Test St"},
            reasons=["Successful eKYC authentication"],
            raw_response={"uid": subject.aadhaar_ref, "status": "Success"}
        )
        
    async def is_available(self) -> bool:
        return True
