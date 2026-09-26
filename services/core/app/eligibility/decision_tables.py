"""Decision tables for all 5 schemes. Rules-as-code, versioned."""

from app.shared.types import SchemeType, ClaimType

PRE_MATRIC_RULES = [
    {
        "id": "pm_class",
        "description": "Student must be in class 9 or 10",
        "check": "student.current_class in [9, 10]",
        "failure_reason": "Pre-Matric is for students in Class 9-10 only"
    },
    {
        "id": "pm_income",
        "description": "Family annual income must not exceed ₹2,50,000 (or ₹3,50,000 for some states)",
        "check": "student.family_income <= 250000",
        "failure_reason": "Family income exceeds the prescribed limit"
    },
    {
        "id": "pm_st",
        "description": "Student must belong to Scheduled Tribe",
        "check": "student.has_attestation('ST_STATUS')",
        "failure_reason": "ST status not verified"
    },
    {
        "id": "pm_enrolment",
        "description": "Student must be enrolled in a recognized school",
        "check": "student.has_attestation('SCHOOL_ENROLMENT')",
        "failure_reason": "School enrolment not verified"
    },
    {
        "id": "pm_one_scheme",
        "description": "Student must not hold another MoTA scholarship",
        "check": "not student.has_active_scholarship()",
        "failure_reason": "Student currently holds another active scholarship"
    }
]

POST_MATRIC_RULES = [
    {
        "id": "postm_class",
        "description": "Student must be in class 11 or above",
        "check": "student.current_class >= 11",
        "failure_reason": "Post-Matric is for students in Class 11 and above"
    },
    {
        "id": "postm_income",
        "description": "Family annual income must not exceed ₹2,50,000",
        "check": "student.family_income <= 250000",
        "failure_reason": "Family income exceeds ₹2,50,000"
    },
    {
        "id": "postm_st",
        "description": "Student must belong to Scheduled Tribe",
        "check": "student.has_attestation('ST_STATUS')",
        "failure_reason": "ST status not verified"
    },
    {
        "id": "postm_one_scheme",
        "description": "Student must not hold another MoTA scholarship",
        "check": "not student.has_active_scholarship()",
        "failure_reason": "Student currently holds another active scholarship"
    }
]

TOP_CLASS_RULES = [
    {
        "id": "tc_admission",
        "description": "Admission to a notified premier institution",
        "check": "student.has_attestation('TOP_CLASS_INSTITUTION')",
        "failure_reason": "Not admitted to a notified premier institution"
    },
    {
        "id": "tc_income",
        "description": "Family annual income must not exceed ₹8,00,000",
        "check": "student.family_income <= 800000",
        "failure_reason": "Family income exceeds ₹8,00,000"
    },
    {
        "id": "tc_st",
        "description": "Student must belong to Scheduled Tribe",
        "check": "student.has_attestation('ST_STATUS')",
        "failure_reason": "ST status not verified"
    }
]

NFST_RULES = [
    {
        "id": "nfst_qualification",
        "description": "Must have qualified NET/JRF",
        "check": "student.has_attestation('NET_JRF')",
        "failure_reason": "NET/JRF qualification not verified"
    },
    {
        "id": "nfst_admission",
        "description": "Registered for M.Phil/PhD",
        "check": "student.has_attestation('HIGHER_ED')",
        "failure_reason": "M.Phil/PhD registration not verified"
    },
    {
        "id": "nfst_st",
        "description": "Student must belong to Scheduled Tribe",
        "check": "student.has_attestation('ST_STATUS')",
        "failure_reason": "ST status not verified"
    }
]

NOS_RULES = [
    {
        "id": "nos_admission",
        "description": "Admission to a foreign university for Master's/PhD/Post-doc",
        "check": "student.has_attestation('FOREIGN_ADMISSION')",
        "failure_reason": "Foreign university admission not verified"
    },
    {
        "id": "nos_income",
        "description": "Family income must not exceed ₹6,00,000",
        "check": "student.family_income <= 600000",
        "failure_reason": "Family income exceeds ₹6,00,000"
    },
    {
        "id": "nos_st",
        "description": "Student must belong to Scheduled Tribe",
        "check": "student.has_attestation('ST_STATUS')",
        "failure_reason": "ST status not verified"
    }
]

SCHEME_LADDER = [
    SchemeType.PRE_MATRIC,
    SchemeType.POST_MATRIC, 
    SchemeType.TOP_CLASS,
    SchemeType.NFST,
    SchemeType.NOS,
]

TRANSITION_TRIGGERS = {
    SchemeType.POST_MATRIC: "Class 10 result or Class 11+ admission",
    SchemeType.TOP_CLASS: "Admission to a notified premier institution",
    SchemeType.NFST: "NET/JRF qualification + M.Phil/PhD registration",
    SchemeType.NOS: "Foreign university admission for Master's/PhD/Post-doc",
}

REQUIRED_ATTESTATIONS = {
    SchemeType.PRE_MATRIC: [ClaimType.IDENTITY, ClaimType.ST_STATUS, ClaimType.INCOME, ClaimType.SCHOOL_ENROLMENT],
    SchemeType.POST_MATRIC: [ClaimType.IDENTITY, ClaimType.ST_STATUS, ClaimType.INCOME, ClaimType.HIGHER_ED, ClaimType.ACADEMIC_RECORDS],
    SchemeType.TOP_CLASS: [ClaimType.IDENTITY, ClaimType.ST_STATUS, ClaimType.INCOME, ClaimType.TOP_CLASS_INSTITUTION],
    SchemeType.NFST: [ClaimType.IDENTITY, ClaimType.ST_STATUS, ClaimType.NET_JRF, ClaimType.HIGHER_ED],
    SchemeType.NOS: [ClaimType.IDENTITY, ClaimType.ST_STATUS, ClaimType.INCOME, ClaimType.FOREIGN_ADMISSION, ClaimType.ACADEMIC_RECORDS],
}

SCHEME_RULES = {
    SchemeType.PRE_MATRIC: PRE_MATRIC_RULES,
    SchemeType.POST_MATRIC: POST_MATRIC_RULES,
    SchemeType.TOP_CLASS: TOP_CLASS_RULES,
    SchemeType.NFST: NFST_RULES,
    SchemeType.NOS: NOS_RULES,
}
