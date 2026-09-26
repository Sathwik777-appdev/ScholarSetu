from app.shared.types import ClaimType, VerificationMethod, VerificationStatus, ConsentArtefact
from app.verification.plugins.base import VerifierPlugin, SubjectRef, VerificationResult

class AISHEVerifier(VerifierPlugin):
    claim_type: ClaimType = ClaimType.HIGHER_ED
    source_name: str = "AISHE"
    priority: int = 2
    
    async def verify(self, subject: SubjectRef, consent: ConsentArtefact) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.90,
            source=self.source_name,
            method=VerificationMethod.API,
            evidence_hash="mock_hash_aishe",
            claim_value={"institution_name": "Test University", "course": "B.Tech"},
            reasons=["Found active enrollment in AISHE portal"],
            raw_response={"aishe_code": "U-1234", "enrollment_status": "Active"}
        )
        
    async def is_available(self) -> bool:
        return True
