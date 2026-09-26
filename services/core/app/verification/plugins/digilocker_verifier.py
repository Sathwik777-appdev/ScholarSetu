from typing import Optional
from app.shared.types import ClaimType, VerificationMethod, VerificationStatus, ConsentArtefact
from app.verification.plugins.base import VerifierPlugin, SubjectRef, VerificationResult

class DigiLockerVerifier(VerifierPlugin):
    claim_type: ClaimType = ClaimType.ST_STATUS  # Verifies multiple but let's say primary is ST_STATUS
    source_name: str = "DigiLocker"
    priority: int = 1
    
    async def verify(self, subject: SubjectRef, consent: ConsentArtefact) -> VerificationResult:
        # Mock Digilocker API call
        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            confidence=0.95,
            source=self.source_name,
            method=VerificationMethod.API,
            evidence_hash="mock_hash_digilocker",
            claim_value={"st_status": "Valid", "income": 50000},
            reasons=["Found valid caste certificate in DigiLocker"],
            raw_response={"document_type": "Caste Certificate", "status": "Active"}
        )
        
    async def is_available(self) -> bool:
        return True
