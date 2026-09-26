from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.shared.types import ClaimType

REQUESTERS = {"SCHOLARSETU_VERIFICATION_MESH", "SCHOLARSETU_WALLET"}
DIGILOCKER_DOCS = {"MARKSHEET_10", "MARKSHEET_12", "CASTE_CERTIFICATE", "INCOME_CERTIFICATE", "AADHAAR"}


class ConsentCreate(BaseModel):
    model_config = {"extra": "forbid"}
    requester: str
    purpose: str = Field(..., min_length=5, max_length=300)
    data_items: list[str] = Field(..., min_length=1, max_length=20)
    duration_days: int = Field(..., ge=1, le=365)

    @field_validator("requester")
    @classmethod
    def _known_requester(cls, v: str) -> str:
        if v not in REQUESTERS:
            raise ValueError(f"requester must be one of {sorted(REQUESTERS)}")
        return v

    @field_validator("data_items")
    @classmethod
    def _known_items(cls, items: list[str]) -> list[str]:
        claims = {c.value for c in ClaimType}
        for item in items:
            if item in claims or (item.startswith("DIGILOCKER:") and item.split(":", 1)[1] in DIGILOCKER_DOCS):
                continue
            raise ValueError(f"unknown data item {item!r}")
        return sorted(set(items))


class ConsentResponse(BaseModel):
    id: str
    student_id: str
    requester: str
    purpose: str
    data_items: list[str]
    granted_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime]
    is_active: bool
