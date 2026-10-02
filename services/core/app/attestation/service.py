"""Issues, verifies and manages verification attestations (the Scholarship Passport).

Every attestation is signed as a compact JWS (EdDSA / Ed25519) over its full content:
subject, claim type and value, source, method, confidence, evidence hash, issued_at,
valid_until and status. Any status change re-signs it. Attestations are stored in Postgres.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.attestation.keys import AttestationSigner, get_signer
from app.attestation.models import Attestation
from app.attestation.schemas import AttestationResponse, AttestationVerification, ScholarshipPassport
from app.database import get_db
from app.shared.ids import new_id
from app.shared.types import AttestationStatus, ClaimType, VerificationMethod

VALIDITY_POLICY: dict[ClaimType, Optional[timedelta]] = {
    ClaimType.IDENTITY: None,
    ClaimType.ST_STATUS: None,
    ClaimType.INCOME: timedelta(days=365),
    ClaimType.DOMICILE: timedelta(days=365 * 3),
    ClaimType.SCHOOL_ENROLMENT: timedelta(days=365),
    ClaimType.HIGHER_ED: timedelta(days=365),
    ClaimType.ACADEMIC_RECORDS: None,
    ClaimType.NET_JRF: None,
}


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def signed_payload(att: Attestation) -> dict[str, Any]:
    """The exact content covered by the signature (ARCHITECTURE.md §6.4.4 field names)."""
    return {
        "iss": AttestationSigner.ISSUER,
        "attestation_id": att.id,
        "subject": att.student_id,
        "claim": {"type": att.claim_type.value, "value": att.claim_value},
        "source": att.source,
        "method": att.method.value,
        "confidence": att.confidence,
        "evidence_hash": att.evidence_hash,
        "issued_at": _iso(_aware(att.issued_at)),
        "valid_until": _iso(_aware(att.valid_until)),
        "status": att.status.value,
    }


def to_response(att: Attestation) -> AttestationResponse:
    return AttestationResponse(
        attestation_id=att.id, student_id=att.student_id, claim_type=att.claim_type, claim_value=att.claim_value,
        source=att.source, method=att.method.value, confidence=att.confidence, evidence_hash=att.evidence_hash,
        issue_date=_aware(att.issued_at), expiry_date=_aware(att.valid_until), signature=att.signature,
        status=att.status.value,
    )


class AttestationService:
    def __init__(self, db: AsyncSession, signer: AttestationSigner):
        self.db = db
        self.signer = signer

    @property
    def jwk(self) -> dict:
        return self.signer.jwk

    def _sign(self, att: Attestation) -> None:
        att.signature = self.signer.sign(signed_payload(att))

    async def get(self, attestation_id: str) -> Optional[Attestation]:
        return await self.db.get(Attestation, attestation_id)

    async def find_valid_attestations(self, student_id: str, claim_types: list[ClaimType]) -> dict[ClaimType, Attestation]:
        """ACTIVE, unexpired attestations (PROVISIONAL ones are never reused as proof)."""
        now = datetime.now(timezone.utc)
        rows = (await self.db.execute(
            select(Attestation).where(Attestation.student_id == student_id,
                                      Attestation.claim_type.in_(claim_types),
                                      Attestation.status == AttestationStatus.ACTIVE)
            .order_by(Attestation.issued_at)
        )).scalars()
        return {a.claim_type: a for a in rows if a.valid_until is None or _aware(a.valid_until) > now}

    async def issue_attestation(self, student_id: str, claim_type: ClaimType, claim_value: dict, source: str,
                                method: VerificationMethod, confidence: float, evidence_hash: Optional[str],
                                status: AttestationStatus = AttestationStatus.ACTIVE) -> Attestation:
        issued_at = datetime.now(timezone.utc)
        validity = VALIDITY_POLICY.get(claim_type)
        att = Attestation(
            id=new_id(), student_id=student_id, claim_type=claim_type, claim_value=claim_value, source=source,
            method=method, confidence=confidence, evidence_hash=evidence_hash, issued_at=issued_at,
            valid_until=issued_at + validity if validity else None, status=status, signature="",
        )
        self._sign(att)
        self.db.add(att)
        await self.db.flush()
        return att

    async def set_status(self, att: Attestation, status: AttestationStatus) -> Attestation:
        """Change status and re-sign, because status is part of the signed content."""
        att.status = status
        self._sign(att)
        await self.db.flush()
        return att

    async def revoke_attestation(self, attestation_id: str) -> None:
        att = await self.get(attestation_id)
        if att is not None:
            await self.set_status(att, AttestationStatus.REVOKED)

    def verify_jws(self, token: str) -> AttestationVerification:
        """Verify a presented attestation JWS on its own (works for anyone holding the public key)."""
        try:
            payload = self.signer.decode(token)
        except jwt.InvalidTokenError:
            return AttestationVerification(is_valid=False, reason="Invalid cryptographic signature")
        if payload.get("status") != AttestationStatus.ACTIVE.value:
            return AttestationVerification(is_valid=False, reason=f"Attestation status is {payload.get('status')}")
        valid_until = payload.get("valid_until")
        if valid_until and datetime.fromisoformat(valid_until) < datetime.now(timezone.utc):
            return AttestationVerification(is_valid=False, reason="Attestation expired", payload=payload)
        return AttestationVerification(is_valid=True, payload=payload)

    async def verify_attestation(self, attestation_id: str) -> AttestationVerification:
        """A stored attestation is valid only if its JWS verifies AND matches every stored field."""
        att = await self.get(attestation_id)
        if att is None:
            return AttestationVerification(is_valid=False, reason="Attestation not found")
        try:
            signed = self.signer.decode(att.signature)
        except jwt.InvalidTokenError:
            return AttestationVerification(is_valid=False, reason="Invalid cryptographic signature")
        if signed != signed_payload(att):
            return AttestationVerification(is_valid=False, reason="Stored attestation does not match its signed content")
        return self.verify_jws(att.signature)

    async def get_passport(self, student_id: str) -> ScholarshipPassport:
        passport: dict[ClaimType, list[AttestationResponse]] = {ct: [] for ct in ClaimType}
        rows = (await self.db.execute(
            select(Attestation).where(Attestation.student_id == student_id).order_by(Attestation.issued_at)
        )).scalars()
        for att in rows:
            passport[att.claim_type].append(to_response(att))
        return ScholarshipPassport(student_id=student_id, attestations=passport)

    async def get_expiring_attestations(self, student_id: str, days_ahead: int = 30) -> list[Attestation]:
        now = datetime.now(timezone.utc)
        target = now + timedelta(days=days_ahead)
        rows = (await self.db.execute(
            select(Attestation).where(Attestation.student_id == student_id,
                                      Attestation.status == AttestationStatus.ACTIVE,
                                      Attestation.valid_until.is_not(None))
        )).scalars()
        return [a for a in rows if now < _aware(a.valid_until) <= target]


def get_attestation_service(db: AsyncSession = Depends(get_db)) -> AttestationService:
    return AttestationService(db, get_signer())
