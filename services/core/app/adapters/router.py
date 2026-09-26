from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.models import ParkedEvent
from app.adapters.sync_service import AdapterSyncService
from app.database import get_db
from app.dependencies import OFFICER_ROLES, require_role
from app.gateway.models import User
from app.gateway.service import record_audit
from app.shared.types import UserRole
from app.verification.sources import SourceClient, get_source_client

router = APIRouter(prefix="/v1/admin/adapters", tags=["Scheme Adapters"])


class ParkedEventOut(BaseModel):
    id: str
    source_system: str
    source_ref: str
    raw_status: str
    reason: str
    application_id: str | None
    created_at: datetime
    resolved_at: datetime | None


@router.post("/sync")
async def sync_now(user: User = Depends(require_role(UserRole.STATE_OFFICER, UserRole.MINISTRY)),
                   db: AsyncSession = Depends(get_db), sources: SourceClient = Depends(get_source_client)):
    """Poll every portal now (the API also polls on ADAPTER_SYNC_INTERVAL_SECONDS)."""
    results = await AdapterSyncService(db, sources).sync_all()
    return {"students": len(results), "imported": sum(len(r.imported) for r in results),
            "transitions": sum(r.transitions for r in results),
            "payments_updated": sum(r.payments_updated for r in results),
            "parked": sum(r.parked for r in results), "errors": [e for r in results for e in r.errors]}


@router.get("/parked", response_model=list[ParkedEventOut])
async def list_parked(include_resolved: bool = False, user: User = Depends(require_role(*OFFICER_ROLES)),
                      db: AsyncSession = Depends(get_db)):
    query = select(ParkedEvent).order_by(ParkedEvent.created_at.desc())
    if not include_resolved:
        query = query.where(ParkedEvent.resolved_at.is_(None))
    return [ParkedEventOut(source_system=p.source_system.value,
                           **{k: getattr(p, k) for k in ParkedEventOut.model_fields if k != "source_system"})
            for p in (await db.execute(query)).scalars()]


@router.post("/parked/{event_id}/resolve", response_model=ParkedEventOut)
async def resolve_parked(event_id: str, user: User = Depends(require_role(UserRole.STATE_OFFICER, UserRole.MINISTRY)),
                         db: AsyncSession = Depends(get_db)):
    """Mark a parked status as handled (e.g. after the state map was extended and the sync re-run)."""
    parked = await db.get(ParkedEvent, event_id)
    if parked is None:
        raise HTTPException(status_code=404, detail="Parked event not found")
    parked.resolved_at = parked.resolved_at or datetime.now(timezone.utc)
    await record_audit(db, "ADAPTER_EVENT_RESOLVED", actor=user, details={"parked_event_id": event_id})
    await db.commit()
    return ParkedEventOut(source_system=parked.source_system.value,
                          **{k: getattr(parked, k) for k in ParkedEventOut.model_fields if k != "source_system"})
