"""Temporal activities: all I/O (database, PFMS) happens here, never in workflow code."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from temporalio import activity

from app.config import settings
from app.database import AsyncSessionLocal
from app.dbt_guardian.models import DbtRetry
from app.dbt_guardian.service import DBTGuardianService
from app.ledger.models import Application
from app.ledger.service import LedgerService
from app.verification.sources import SourceClient

TIERS = ["INSTITUTE_OFFICER", "DISTRICT_OFFICER", "STATE_OFFICER"]
# Stages the institute owns escalate institute -> district -> state; stages the district/state
# authority owns start at the district officer (the institute cannot act on them).
INSTITUTE_STAGES = {"SUBMITTED", "INSTITUTE_VERIFICATION", "RESUBMITTED"}


def escalation_chain(state: str) -> list[str]:
    return TIERS if state in INSTITUTE_STAGES else TIERS[1:]


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


@activity.defn
async def sla_snapshot(application_id: str) -> dict:
    """Current stage, when it began, and its SLA (None when the stage has no SLA or the app is gone)."""
    async with AsyncSessionLocal() as db:
        app = await db.get(Application, application_id)
        if app is None:
            return {"state": None, "state_changed_at": None, "sla_seconds": None, "escalation_seconds": None, "tiers": 0}
        return {"state": app.canonical_state.value, "state_changed_at": _utc(app.state_changed_at).isoformat(),
                "tiers": len(escalation_chain(app.canonical_state.value)),
                "sla_seconds": settings.sla_seconds(app.canonical_state),
                "escalation_seconds": settings.escalation_seconds}


@activity.defn
async def record_sla_breach(application_id: str, state: str, state_changed_at: str, tier: int) -> dict:
    """Record the breach in the ledger (topic sla.breached) if the application is still stuck in that stage."""
    async with AsyncSessionLocal() as db:
        app = await db.get(Application, application_id)
        if app is None or app.canonical_state.value != state or _utc(app.state_changed_at).isoformat() != state_changed_at:
            return {"breached": False}
        days = (datetime.now(timezone.utc) - _utc(app.state_changed_at)).total_seconds() / 86400
        chain = escalation_chain(state)
        tier_role = chain[min(tier, len(chain) - 1)]
        event = await LedgerService(db).append_event(app, "SLABreached", {
            "stage": state, "days_in_stage": round(days, 2),
            "sla_days": round((settings.sla_seconds(app.canonical_state) or 0) / 86400, 3),
            "escalated_to": tier_role, "tier": tier}, actor="system:sla-monitor")
        await db.commit()
        return {"breached": True, "event_id": event.event_id, "escalated_to": tier_role}


@activity.defn
async def open_sla_applications() -> list[str]:
    async with AsyncSessionLocal() as db:
        states = list(settings.sla_days)
        return list((await db.execute(select(Application.id).where(Application.canonical_state.in_(states)))).scalars())


@activity.defn
async def submitted_dbt_retries() -> list[str]:
    async with AsyncSessionLocal() as db:
        return list((await db.execute(select(DbtRetry.id).where(DbtRetry.status == "SUBMITTED"))).scalars())


@activity.defn
async def settle_dbt_retry(retry_id: str) -> Optional[str]:
    """Ask PFMS about a submitted retry; returns CREDITED / FAILED, or SUBMITTED while still pending."""
    client = SourceClient(settings.MOCK_SERVICE_URL)
    try:
        async with AsyncSessionLocal() as db:
            retry = await db.get(DbtRetry, retry_id)
            if retry is None:
                return None
            if retry.status == "SUBMITTED":
                await DBTGuardianService(db, client).settle_retry(retry, "system:dbt-retry-workflow")
                await db.commit()
            return retry.status
    finally:
        await client.aclose()
