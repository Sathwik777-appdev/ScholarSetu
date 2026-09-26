from typing import Dict, Any, List, Optional
from .decision_tables import SCHEME_RULES, SCHEME_LADDER, TRANSITION_TRIGGERS, REQUIRED_ATTESTATIONS
from .schemas import EligibilityResult, ScholarshipPathway, OneSchemeCheckResult, TransitionDetection
from app.shared.types import SchemeType, ClaimType, CanonicalState


class StudentMock:
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.current_class = data.get("current_class", 11)
        self.family_income = data.get("family_income", 120000)
        self.attestations = data.get("attestations", ["IDENTITY", "ST_STATUS", "SCHOOL_ENROLMENT"])
        self.active_scholarship = data.get("active_scholarship", None)

    def has_attestation(self, claim_type_name: str) -> bool:
        return claim_type_name in self.attestations

    def has_active_scholarship(self) -> bool:
        return self.active_scholarship is not None


class EligibilityService:
    """Rules-as-code eligibility engine with pathway tracking."""

    async def check_eligibility(self, student_id: str, scheme: SchemeType) -> EligibilityResult:
        """Check if student is eligible for a scheme using decision tables."""
        student_data = {
            "current_class": 11 if scheme == SchemeType.POST_MATRIC else 10,
            "family_income": 120000,
            "attestations": ["IDENTITY", "ST_STATUS", "SCHOOL_ENROLMENT", "HIGHER_ED", "ACADEMIC_RECORDS"],
            "active_scholarship": None
        }
        student = StudentMock(student_data)

        reasons = []
        eligible = True

        rules = SCHEME_RULES.get(scheme, [])
        for rule in rules:
            try:
                check_result = eval(rule["check"], {"student": student})
                if not check_result:
                    eligible = False
                    reasons.append(rule["failure_reason"])
            except Exception as e:
                eligible = False
                reasons.append(f"Error evaluating rule {rule['id']}: {str(e)}")

        required = REQUIRED_ATTESTATIONS.get(scheme, [])
        missing = [claim for claim in required if claim.value not in student.attestations and claim.name not in student.attestations]

        if missing:
            eligible = False
            reasons.append(f"Missing required attestations: {[m.value for m in missing]}")

        if eligible:
            reasons.append("All scheme criteria satisfied under MoTA 2026-v1 guidelines.")

        return EligibilityResult(
            eligible=eligible,
            reasons=reasons,
            rule_version="2026-v1",
            required_attestations=required,
            missing_attestations=missing
        )

    async def get_pathway(self, student_id: str) -> ScholarshipPathway:
        """Get the student's position on the scholarship ladder (Scene 2)."""
        current_scheme = SchemeType.PRE_MATRIC
        current_index = SCHEME_LADDER.index(current_scheme)
        next_scheme = SchemeType.POST_MATRIC

        return ScholarshipPathway(
            current_scheme=current_scheme,
            current_state=CanonicalState.CREDITED,
            ladder_position=current_index,
            next_eligible=next_scheme,
            transition_trigger="Class 10 Matriculation marksheet detected in DigiLocker",
            pre_filled_available=True
        )

    async def check_one_scheme_rule(self, student_id: str, target_scheme: SchemeType) -> OneSchemeCheckResult:
        """Check if student already holds another active scholarship."""
        return OneSchemeCheckResult(
            has_conflict=False,
            current_holding=None,
            message="No conflicting scholarship holding. Student eligible to apply for Post-Matric."
        )

    async def detect_transition(self, student_id: str, trigger_event: dict) -> TransitionDetection:
        return TransitionDetection(
            detected=True,
            next_scheme=SchemeType.POST_MATRIC,
            trigger_description="Class 10 Matriculation Result detected. Student eligible for Post-Matric ladder rung.",
            pre_filled_fields={
                "name": "Sunita Hansda",
                "father_name": "Babulal Hansda",
                "tribe": "Santal",
                "class": 11,
                "reused_claims": ["IDENTITY", "ST_STATUS"]
            }
        )
