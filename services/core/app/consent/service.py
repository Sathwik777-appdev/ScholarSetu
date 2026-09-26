"""Consent Manager (ARCHITECTURE.md §6.9). Every data pull must name a valid consent that covers it."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.consent.models import Consent
from app.consent.schemas import ConsentResponse
from app.gateway.models import User
from app.gateway.service import record_audit
from app.shared.events import emit
from app.shared.types import ConsentArtefact


class ConsentError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def to_response(c: Consent) -> ConsentResponse:
    now = datetime.now(timezone.utc)
    return ConsentResponse(id=c.id, student_id=c.student_id, requester=c.requester, purpose=c.purpose,
                           data_items=c.data_items, granted_at=c.granted_at, expires_at=c.expires_at,
                           revoked_at=c.revoked_at, is_active=c.revoked_at is None and _aware(c.expires_at) > now)


class ConsentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def grant(self, student_id: str, requester: str, purpose: str, data_items: list[str], duration_days: int,
                    actor: User) -> Consent:
        consent = Consent(student_id=student_id, requester=requester, purpose=purpose, data_items=data_items,
                          granted_by=actor.id, expires_at=datetime.now(timezone.utc) + timedelta(days=duration_days))
        self.db.add(consent)
        await self.db.flush()
        await record_audit(self.db, "CONSENT_GRANTED", actor=actor, student_id=student_id,
                           details={"consent_id": consent.id, "requester": requester, "data_items": data_items})
        await emit(self.db, "consent.granted", "ConsentGranted",
                   {"student_id": student_id, "consent_id": consent.id, "data_items": data_items})
        return consent

    async def list_for(self, student_id: str) -> list[Consent]:
        return list((await self.db.execute(select(Consent).where(Consent.student_id == student_id)
                                           .order_by(Consent.granted_at.desc()))).scalars())

    async def revoke(self, consent_id: str, student_id: str, actor: User) -> Consent:
        consent = await self.db.get(Consent, consent_id)
        if consent is None or consent.student_id != student_id:
            raise ConsentError(404, "Consent not found")
        if consent.revoked_at is None:
            consent.revoked_at = datetime.now(timezone.utc)
            await record_audit(self.db, "CONSENT_REVOKED", actor=actor, student_id=student_id,
                               details={"consent_id": consent_id})
            await emit(self.db, "consent.revoked", "ConsentRevoked", {"student_id": student_id, "consent_id": consent_id})
        return consent

    async def require(self, consent_id: str, student_id: str, requester: str, items: list[str]) -> ConsentArtefact:
        """Return the artefact if the consent is the student's, unexpired, unrevoked and covers every item."""
        consent = await self.db.get(Consent, consent_id) if consent_id else None
        if consent is None or consent.student_id != student_id:
            raise ConsentError(403, "No consent found for this data pull; ask the student to grant one")
        if consent.revoked_at is not None:
            raise ConsentError(403, "This consent was revoked by the student")
        if _aware(consent.expires_at) <= datetime.now(timezone.utc):
            raise ConsentError(403, "This consent has expired")
        if consent.requester != requester:
            raise ConsentError(403, f"This consent was given to {consent.requester}, not {requester}")
        missing = sorted(set(items) - set(consent.data_items))
        if missing:
            raise ConsentError(403, f"The consent does not cover: {', '.join(missing)}")
        return ConsentArtefact(consent_id=consent.id, student_id=student_id, requester=requester,
                               purpose=consent.purpose, data_items=consent.data_items,
                               granted_at=consent.granted_at.isoformat(), expires_at=consent.expires_at.isoformat())
