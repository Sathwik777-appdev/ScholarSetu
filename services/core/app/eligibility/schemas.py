from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.shared.types import SchemeType, ClaimType, CanonicalState

class EligibilityCheckRequest(BaseModel):
    student_id: str
    scheme: SchemeType

class EligibilityResult(BaseModel):
    eligible: bool
    reasons: List[str] = Field(default_factory=list)
    rule_version: str = "1.0"
    required_attestations: List[ClaimType] = Field(default_factory=list)
    missing_attestations: List[ClaimType] = Field(default_factory=list)

class ScholarshipPathway(BaseModel):
    current_scheme: Optional[SchemeType]
    current_state: Optional[CanonicalState]
    ladder_position: int
    next_eligible: Optional[SchemeType]
    transition_trigger: Optional[str]
    pre_filled_available: bool

class OneSchemeCheckResult(BaseModel):
    has_conflict: bool
    current_holding: Optional[SchemeType]
    message: str

class TransitionDetection(BaseModel):
    detected: bool
    next_scheme: Optional[SchemeType]
    trigger_description: Optional[str]
    pre_filled_fields: Dict[str, Any] = Field(default_factory=dict)
