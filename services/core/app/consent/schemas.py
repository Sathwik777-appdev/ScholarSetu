from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from app.shared.types import ClaimType

class ConsentBase(BaseModel):
    requester: str
    data_items: List[str]
    purpose: str
    duration_days: int

class ConsentCreate(ConsentBase):
    pass

class ConsentResponse(ConsentBase):
    id: str
    student_id: str
    created_at: datetime
    expires_at: datetime
    is_active: bool

class ConsentArtefact(BaseModel):
    consent_id: str
    claim_types: List[ClaimType]
    verification_token: str
