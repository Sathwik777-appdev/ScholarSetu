from app.shared.types import ClaimType, VerificationMethod, VerificationStatus, ConsentArtefact
from app.verification.plugins.base import VerifierPlugin, SubjectRef, VerificationResult

class NTAVerifier(VerifierPlugin):
    claim_type: ClaimType = ClaimType.NET_JRF
    source_name: str = "NTA"
    priority: int = 1
    
    async def verify(self, subject: SubjectRef, consent: ConsentArtefact) -> VerificationResult:
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.99,
            source=self.source_name,
            method=VerificationMethod.API,
            evidence_hash="mock_hash_nta",
            claim_value={"qualification": "JRF", "year": 2023},
            reasons=["Found valid NET/JRF qualification"],
            raw_response={"exam": "UGC NET", "result": "Qualified for JRF"}
        )
        
    async def is_available(self) -> bool:
        return True
