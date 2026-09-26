import uuid
from datetime import datetime, timedelta
from typing import List
from app.shared.types import ClaimType
from .schemas import ConsentResponse, ConsentArtefact

class ConsentService:
    """DEPA-style consent management."""
    
    async def create_consent(self, student_id: str, requester: str, data_items: List[str], purpose: str, duration_days: int) -> ConsentResponse:
        """Create a new consent artefact."""
        now = datetime.utcnow()
        expires_at = now + timedelta(days=duration_days)
        
        return ConsentResponse(
            id=str(uuid.uuid4()),
            student_id=student_id,
            requester=requester,
            data_items=data_items,
            purpose=purpose,
            duration_days=duration_days,
            created_at=now,
            expires_at=expires_at,
            is_active=True
        )
    
    async def verify_consent(self, consent_id: str, requester: str, data_item: str) -> bool:
        """Verify a consent artefact is valid for the requested access."""
        # Mock logic
        return True
    
    async def revoke_consent(self, consent_id: str, student_id: str) -> None:
        """Revoke a consent (student-initiated)."""
        pass
    
    async def list_consents(self, student_id: str) -> List[ConsentResponse]:
        """List all consents for a student."""
        return []
    
    async def create_artefact_for_verification(self, student_id: str, claim_types: List[ClaimType]) -> ConsentArtefact:
        """Create a consent artefact specifically for verification flow."""
        return ConsentArtefact(
            consent_id=str(uuid.uuid4()),
            claim_types=claim_types,
            verification_token=str(uuid.uuid4())
        )
