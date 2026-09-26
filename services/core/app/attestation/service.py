"""Issues, verifies and manages verification attestations (the Scholarship Passport).

Every attestation is signed as a compact JWS (EdDSA / Ed25519) over its full content:
subject, claim type and value, source, method, confidence, evidence hash, issued_at,
valid_until and status. Changing any of these without the signing key is detectable.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.attestation.keys import load_or_create_signing_key, public_jwk
from app.attestation.schemas import AttestationResponse, AttestationVerification, ScholarshipPassport
from app.config import settings
from app.shared.ids import new_id
from app.shared.types import ClaimType

ISSUER = "scholarsetu"


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


class AttestationService:
    """Attestation store is in memory until the Phase 4 persistence work; the signing key is persistent."""

    def __init__(self, private_key: Ed25519PrivateKey, db=None):
        self.db = db
        self.private_key = private_key
        self.public_key = private_key.public_key()
        self.jwk = public_jwk(self.public_key)
        self._store: dict[str, AttestationResponse] = {}
        self._seed_demo_attestations()

    # ── signing ─────────────────────────────────────────────

    @staticmethod
    def signed_payload(att: AttestationResponse) -> dict[str, Any]:
        """The exact content covered by the signature (ARCHITECTURE.md §6.4.4 field names)."""
        return {
            "iss": ISSUER,
            "attestation_id": att.attestation_id,
            "subject": att.student_id,
            "claim": {"type": att.claim_type.value, "value": att.claim_value},
            "source": att.source,
            "method": att.method,
            "confidence": att.confidence,
            "evidence_hash": att.evidence_hash,
            "issued_at": _iso(att.issue_date),
            "valid_until": _iso(att.expiry_date),
            "status": att.status,
        }

    def _sign(self, att: AttestationResponse) -> str:
        return jwt.encode(self.signed_payload(att), self.private_key, algorithm="EdDSA",
                          headers={"kid": self.jwk["kid"], "typ": "JWT"})

    def decode_jws(self, token: str) -> dict[str, Any]:
        """Verify the signature and return the payload. Raises jwt.InvalidTokenError if it does not verify."""
        return jwt.decode(token, self.public_key, algorithms=["EdDSA"], issuer=ISSUER,
                          options={"verify_exp": False, "verify_aud": False})

    # ── demo data (moves to scripts/seed_demo.py in Phase 4) ─

    def _seed_demo_attestations(self):
        now = datetime.now(timezone.utc)
        student_id = "stu-sunita-001"
        seeds = [
            (ClaimType.ST_STATUS, {"tribe": "Santal", "state": "Jharkhand", "pvtg": False,
                                   "certificate_no": "JH/ST/2022/8821"}, "DIGILOCKER", 0.99,
             "sha256:4a8b9c0d1e2f3a4b", now - timedelta(days=300), None, "ACTIVE"),
            (ClaimType.IDENTITY, {"name": "Sunita Hansda", "dob": "2008-04-12", "gender": "FEMALE",
                                  "aadhaar_masked": "XXXX-XXXX-4912"}, "UIDAI", 1.0,
             "sha256:9f8e7d6c5b4a3a2b", now - timedelta(days=300), None, "ACTIVE"),
            (ClaimType.INCOME, {"annual_income": 120000, "financial_year": "2024-25", "issued_by": "CO Dumka"},
             "EDISTRICT", 0.95, "sha256:1a2b3c4d5e6f7a8b", now - timedelta(days=400), now - timedelta(days=35),
             "EXPIRED"),
        ]
        for claim_type, value, source, confidence, evidence, issued, valid_until, status in seeds:
            att = AttestationResponse(
                attestation_id=new_id(), student_id=student_id, claim_type=claim_type, claim_value=value,
                source=source, method="API", confidence=confidence, evidence_hash=evidence,
                issue_date=issued, expiry_date=valid_until, signature="", status=status,
            )
            att.signature = self._sign(att)
            self._store[att.attestation_id] = att

    # ── lifecycle ───────────────────────────────────────────

    async def find_valid_attestations(self, student_id: str, claim_types: list[ClaimType]) -> dict[ClaimType, AttestationResponse]:
        """Find existing valid (non-expired, non-revoked) attestations."""
        valid = {}
        now = datetime.now(timezone.utc)
        for att in self._store.values():
            if att.student_id == student_id and att.claim_type in claim_types and att.status == "ACTIVE":
                if att.expiry_date is None or att.expiry_date > now:
                    valid[att.claim_type] = att
        return valid

    async def issue_attestation(self, student_id: str, claim_type: ClaimType, claim_value: dict, source: str,
                                method: str, confidence: float, evidence_hash: Optional[str],
                                status: str = "ACTIVE") -> AttestationResponse:
        issue_date = datetime.now(timezone.utc)
        validity = self._get_validity_policy(claim_type)
        att = AttestationResponse(
            attestation_id=new_id(), student_id=student_id, claim_type=claim_type, claim_value=claim_value,
            source=source, method=method, confidence=confidence, evidence_hash=evidence_hash,
            issue_date=issue_date, expiry_date=issue_date + validity if validity else None,
            signature="", status=status,
        )
        att.signature = self._sign(att)
        self._store[att.attestation_id] = att
        return att

    def verify_jws(self, token: str) -> AttestationVerification:
        """Verify a presented attestation JWS on its own (works for anyone holding the public key)."""
        try:
            payload = self.decode_jws(token)
        except jwt.InvalidTokenError:
            return AttestationVerification(is_valid=False, reason="Invalid cryptographic signature")
        if payload.get("status") != "ACTIVE":
            return AttestationVerification(is_valid=False, reason=f"Attestation status is {payload.get('status')}")
        valid_until = payload.get("valid_until")
        if valid_until and datetime.fromisoformat(valid_until) < datetime.now(timezone.utc):
            return AttestationVerification(is_valid=False, reason="Attestation expired")
        return AttestationVerification(is_valid=True)

    async def verify_attestation(self, attestation_id: str) -> AttestationVerification:
        """Verify a stored attestation: its JWS must verify AND match every stored field."""
        att = self._store.get(attestation_id)
        if att is None:
            return AttestationVerification(is_valid=False, reason="Attestation not found")
        try:
            signed = self.decode_jws(att.signature)
        except jwt.InvalidTokenError:
            return AttestationVerification(is_valid=False, reason="Invalid cryptographic signature")
        if signed != self.signed_payload(att):
            return AttestationVerification(is_valid=False, reason="Stored attestation does not match its signed content")
        return self.verify_jws(att.signature)

    async def revoke_attestation(self, attestation_id: str, reason: str) -> None:
        att = self._store.get(attestation_id)
        if att is not None:
            att.status = "REVOKED"
            att.signature = self._sign(att)  # status is signed, so re-sign on every status change

    async def get_passport(self, student_id: str) -> ScholarshipPassport:
        passport = {ct: [] for ct in ClaimType}
        for att in self._store.values():
            if att.student_id == student_id:
                passport[att.claim_type].append(att)
        return ScholarshipPassport(student_id=student_id, attestations=passport)

    def get_owner(self, attestation_id: str) -> Optional[str]:
        att = self._store.get(attestation_id)
        return att.student_id if att else None

    async def get_expiring_attestations(self, student_id: str, days_ahead: int = 30) -> list[AttestationResponse]:
        expiring = []
        now = datetime.now(timezone.utc)
        target = now + timedelta(days=days_ahead)
        for att in self._store.values():
            if att.student_id == student_id and att.status == "ACTIVE" and att.expiry_date:
                if now < att.expiry_date <= target:
                    expiring.append(att)
        return expiring

    def _get_validity_policy(self, claim_type: ClaimType) -> Optional[timedelta]:
        policies = {
            ClaimType.ST_STATUS: None,
            ClaimType.INCOME: timedelta(days=365),
            ClaimType.SCHOOL_ENROLMENT: timedelta(days=365),
            ClaimType.HIGHER_ED: timedelta(days=365),
            ClaimType.ACADEMIC_RECORDS: None,
            ClaimType.NET_JRF: None,
            ClaimType.IDENTITY: None,
            ClaimType.DOMICILE: timedelta(days=365 * 3),
        }
        return policies.get(claim_type)


_service: Optional[AttestationService] = None


def get_attestation_service() -> AttestationService:
    """Process-wide service. Loading the key here makes startup fail fast if it is unavailable."""
    global _service
    if _service is None:
        key = load_or_create_signing_key(settings.ATTESTATION_PRIVATE_KEY_PATH, settings.DEMO_MODE)
        _service = AttestationService(key)
    return _service


def reset_attestation_service() -> None:
    """Drop the cached service (tests use this to simulate a restart)."""
    global _service
    _service = None
