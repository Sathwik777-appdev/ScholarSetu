"""Shared types and enums for the ScholarSetu platform.

All canonical types used across modules are defined here to ensure consistency.
"""

from enum import Enum
from pydantic import BaseModel


# ── Scholarship Scheme Types ────────────────────────────────

class SchemeType(str, Enum):
    """The five MoTA scholarship schemes."""
    PRE_MATRIC = "PRE_MATRIC"
    POST_MATRIC = "POST_MATRIC"
    TOP_CLASS = "TOP_CLASS"
    NFST = "NFST"
    NOS = "NOS"


# ── Source Systems (portals) ────────────────────────────────

class SourceSystem(str, Enum):
    """External scholarship portals we integrate with."""
    NSP = "NSP"               # National Scholarship Portal
    SFMP = "SFMP"             # Scholarship Fellowship Management Portal
    NOS_PORTAL = "NOS_PORTAL" # National Overseas Scholarship Portal
    SCHOLARSETU = "SCHOLARSETU"  # Events originating from our system


# ── Canonical Application Lifecycle ─────────────────────────

class CanonicalState(str, Enum):
    """Canonical lifecycle states for a scholarship application.
    
    All source-system-specific states are mapped to these.
    See adapters/<source>/state_map.yaml for mappings.
    """
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    INSTITUTE_VERIFICATION = "INSTITUTE_VERIFICATION"
    DEFICIENCY_RAISED = "DEFICIENCY_RAISED"
    RESUBMITTED = "RESUBMITTED"
    AUTHORITY_VERIFICATION = "AUTHORITY_VERIFICATION"
    SANCTIONED = "SANCTIONED"
    REJECTED = "REJECTED"
    PAYMENT_INITIATED = "PAYMENT_INITIATED"
    CREDITED = "CREDITED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    RENEWAL_DUE = "RENEWAL_DUE"


# ── Verification ────────────────────────────────────────────

class ClaimType(str, Enum):
    """Types of claims that can be verified and attested."""
    IDENTITY = "IDENTITY"
    ST_STATUS = "ST_STATUS"
    INCOME = "INCOME"
    DOMICILE = "DOMICILE"
    SCHOOL_ENROLMENT = "SCHOOL_ENROLMENT"
    HIGHER_ED = "HIGHER_ED"
    ACADEMIC_RECORDS = "ACADEMIC_RECORDS"
    NET_JRF = "NET_JRF"
    DISABILITY = "DISABILITY"
    TOP_CLASS_INSTITUTION = "TOP_CLASS_INSTITUTION"
    FOREIGN_ADMISSION = "FOREIGN_ADMISSION"


class VerificationMethod(str, Enum):
    """How a claim was verified."""
    API = "API"                    # Source-of-truth API (preferred)
    OCR_ASSISTED = "OCR_ASSISTED"  # OCR on uploaded document (fallback)
    DOCUMENT = "DOCUMENT"          # Manual document inspection
    MANUAL = "MANUAL"              # Manual officer verification


class VerificationStatus(str, Enum):
    """Outcome of a verification attempt."""
    VERIFIED = "VERIFIED"
    PROVISIONAL = "PROVISIONAL"
    FAILED = "FAILED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"


class AttestationStatus(str, Enum):
    """Lifecycle status of a verification attestation."""
    ACTIVE = "ACTIVE"
    PROVISIONAL = "PROVISIONAL"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class ReviewDecision(str, Enum):
    """Officer decision on a manual review case."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_MORE_INFO = "NEEDS_MORE_INFO"


# ── Payments ────────────────────────────────────────────────

class PaymentState(str, Enum):
    """DBT payment states."""
    INITIATED = "INITIATED"
    CREDITED = "CREDITED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


# ── Notifications ───────────────────────────────────────────

class NotificationChannel(str, Enum):
    """Channels for sending notifications."""
    PUSH = "PUSH"
    SMS = "SMS"
    IVR = "IVR"
    WHATSAPP = "WHATSAPP"
    JAGO = "JAGO"
    EMAIL = "EMAIL"


# ── Access Control ──────────────────────────────────────────

class UserRole(str, Enum):
    """User roles in the system."""
    STUDENT = "STUDENT"
    GUARDIAN = "GUARDIAN"
    MITRA = "MITRA"
    INSTITUTE_OFFICER = "INSTITUTE_OFFICER"
    DISTRICT_OFFICER = "DISTRICT_OFFICER"
    STATE_OFFICER = "STATE_OFFICER"
    MINISTRY = "MINISTRY"


class MitraScope(str, Enum):
    """Scoped permissions for Mitra (assisted) mode. There is deliberately no full-access scope."""
    UPLOAD_DOCUMENTS = "UPLOAD_DOCUMENTS"
    VIEW_STATUS = "VIEW_STATUS"
    RESPOND_DEFICIENCY = "RESPOND_DEFICIENCY"


class AssistSessionStatus(str, Enum):
    """Lifecycle of a Mitra assist session."""
    PENDING_STUDENT_OTP = "PENDING_STUDENT_OTP"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"


class OtpPurpose(str, Enum):
    LOGIN = "LOGIN"
    MITRA_CONSENT = "MITRA_CONSENT"


class Gender(str, Enum):
    """Gender options."""
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


# ── Consent ─────────────────────────────────────────────────

class ConsentArtefact(BaseModel):
    """DEPA-style consent artefact for data access."""
    consent_id: str
    student_id: str
    requester: str
    purpose: str
    data_items: list[str] = []
    granted_at: str
    expires_at: str
