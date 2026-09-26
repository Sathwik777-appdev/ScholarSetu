from typing import Optional

from pydantic import BaseModel, Field

from app.shared.types import CanonicalState, ClaimType, SchemeType


class RuleOutcome(BaseModel):
    rule_id: str
    outcome: str            # PASS | FAIL | NEEDS
    detail: str


class EligibilityResult(BaseModel):
    scheme: SchemeType
    status: str             # ELIGIBLE | NOT_ELIGIBLE | NEEDS_INFORMATION
    eligible: bool
    reasons: list[str]
    missing: list[str] = Field(default_factory=list)
    rule_version: str
    rule_version_id: str
    rules: list[RuleOutcome]
    required_attestations: list[ClaimType]
    decision_id: Optional[str] = None


class OneSchemeCheck(BaseModel):
    has_conflict: bool
    blocking: bool
    current_holding: Optional[SchemeType] = None
    holding_application_id: Optional[str] = None
    message: str


class ScholarshipPathway(BaseModel):
    current_scheme: Optional[SchemeType]
    current_state: Optional[CanonicalState]
    current_application_id: Optional[str]
    ladder: list[SchemeType]
    ladder_position: Optional[int]
    education_stage: Optional[str]
    next_eligible: Optional[SchemeType]
    transition_trigger: Optional[str]
    prefilled_application_id: Optional[str]
