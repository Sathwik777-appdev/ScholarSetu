"""Portal → ledger sync. Imports portal applications, walks the canonical state machine along valid
transitions (events attributed to the portal), syncs payments, and parks anything it cannot apply."""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.models import ParkedEvent
from app.adapters.portal import PortalAdapter, default_adapters
from app.gateway.service import record_audit
from app.ledger.models import Application, Payment
from app.ledger.service import VALID_TRANSITIONS, LedgerError, LedgerService
from app.shared.events import emit
from app.shared.types import CanonicalState, PaymentState, SchemeType
from app.students.models import Student
from app.verification.sources import SourceClient, SourceUnavailable

logger = logging.getLogger("scholarsetu.adapters")

PAYMENT_DRIVEN = {CanonicalState.PAYMENT_INITIATED, CanonicalState.CREDITED, CanonicalState.PAYMENT_FAILED}
PAYMENT_PATHS = {PaymentState.INITIATED: [PaymentState.INITIATED],
                 PaymentState.CREDITED: [PaymentState.INITIATED, PaymentState.CREDITED],
                 PaymentState.FAILED: [PaymentState.INITIATED, PaymentState.FAILED]}


@dataclass
class SyncResult:
    student_id: str
    imported: list[str] = field(default_factory=list)
    transitions: int = 0
    payments_updated: int = 0
    parked: int = 0
    errors: list[str] = field(default_factory=list)


def shortest_path(start: CanonicalState, goal: CanonicalState) -> Optional[list[CanonicalState]]:
    queue, seen = deque([[start]]), {start}
    while queue:
        path = queue.popleft()
        if path[-1] == goal:
            return path[1:]
        for nxt in VALID_TRANSITIONS.get(path[-1], set()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(path + [nxt])
    return None


def _ts(value: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(value) if value else None


class AdapterSyncService:
    def __init__(self, db: AsyncSession, sources: SourceClient, adapters: Optional[list[PortalAdapter]] = None):
        self.db = db
        self.sources = sources
        self.ledger = LedgerService(db)
        self.adapters = adapters if adapters is not None else default_adapters()

    async def _park(self, adapter: PortalAdapter, portal_app: dict, reason: str,
                    application_id: Optional[str], result: SyncResult) -> None:
        existing = (await self.db.execute(select(ParkedEvent).where(
            ParkedEvent.source_ref == portal_app["app_id"], ParkedEvent.raw_status == portal_app["status"],
            ParkedEvent.resolved_at.is_(None)))).scalar_one_or_none()
        if existing is not None:
            return  # already parked and alerted
        parked = ParkedEvent(source_system=adapter.source, source_ref=portal_app["app_id"],
                             raw_status=portal_app["status"], reason=reason, payload=portal_app,
                             application_id=application_id)
        self.db.add(parked)
        await self.db.flush()
        await record_audit(self.db, "ADAPTER_EVENT_PARKED", details={"parked_event_id": parked.id, "reason": reason,
                                                                    "source": adapter.source.value})
        await emit(self.db, "adapter.state_parked", "AdapterStateParked",
                   {"parked_event_id": parked.id, "source": adapter.source.value, "source_ref": portal_app["app_id"],
                    "raw_status": portal_app["status"], "reason": reason, "application_id": application_id})
        logger.warning("parked %s %s status %r: %s", adapter.source.value, portal_app["app_id"],
                       portal_app["status"], reason)
        result.parked += 1

    async def sync_student(self, student: Student) -> SyncResult:
        result = SyncResult(student_id=student.id)
        if not student.aadhaar_ref_token:
            return result
        for adapter in self.adapters:
            try:
                portal_apps = await adapter.list_applications(self.sources, student.aadhaar_ref_token)
            except SourceUnavailable as exc:
                result.errors.append(f"{adapter.source.value}: {exc}")
                continue
            for portal_app in portal_apps:
                # Each application syncs in its own savepoint: one malformed record is parked and the rest
                # of the student's (and everyone else's) records still sync.
                try:
                    async with self.db.begin_nested():
                        await self._sync_application(adapter, student, portal_app, result)
                except Exception as exc:  # noqa: BLE001 - anything unexpected is parked, never fatal
                    logger.exception("portal record %s could not be synced", portal_app.get("app_id"))
                    await self._park(adapter, {"app_id": str(portal_app.get("app_id", "?")),
                                               "status": str(portal_app.get("status", ""))},
                                     f"Could not sync this record: {type(exc).__name__}: {exc}", None, result)
        await self.db.commit()
        return result

    async def _sync_application(self, adapter: PortalAdapter, student: Student, portal_app: dict,
                                result: SyncResult) -> None:
        actor = f"source:{adapter.source.value}"
        target = adapter.map.state(portal_app["status"])
        app = (await self.db.execute(select(Application).where(
            Application.source_system == adapter.source, Application.source_ref == portal_app["app_id"]))
        ).scalar_one_or_none()
        if target is None:
            await self._park(adapter, portal_app, f"Unknown {adapter.source.value} status {portal_app['status']!r}",
                             app.id if app else None, result)
            return
        if app is None:
            scheme = SchemeType(portal_app["scheme"])  # an unknown scheme raises and is parked by the caller
            existing = (await self.db.execute(select(Application).where(
                Application.student_id == student.id, Application.scheme == scheme,
                Application.academic_year == portal_app["academic_year"],
                Application.canonical_state.notin_([CanonicalState.REJECTED, CanonicalState.SURRENDERED])))
            ).scalars().first()
            if existing is not None:
                await self._park(adapter, portal_app, f"Possible duplicate of {existing.id} (same student, scheme "
                                                      f"and year); link or reject it before importing", existing.id,
                                 result)
                return
            from app.eligibility.service import EligibilityService
            held = [h for h in await EligibilityService(self.db).active_holdings(student.id, portal_app["academic_year"])
                    if h.scheme != scheme]
            app = await self.ledger.create_application(
                student.id, SchemeType(portal_app["scheme"]), portal_app["academic_year"], actor,
                {"imported_from": adapter.source.value}, source_system=adapter.source,
                source_ref=portal_app["app_id"],
                initial_state=CanonicalState.DRAFT if target == CanonicalState.DRAFT else CanonicalState.SUBMITTED,
                occurred_at=_ts(portal_app.get("submitted_at")))
            result.imported.append(app.id)
            if held:  # the portal shows a second scholarship for the same year: flag it for the officer
                app.provisional_flags = [f"ONE_SCHEME_CONFLICT:{held[0].id}"]
                await self._park(adapter, portal_app, f"Student also holds {held[0].scheme.value} ({held[0].id}) "
                                                      f"for {portal_app['academic_year']}", app.id, result)

        state_goal = CanonicalState.SANCTIONED if target in PAYMENT_DRIVEN else target
        if app.canonical_state not in PAYMENT_DRIVEN and app.canonical_state != state_goal:
            path = shortest_path(app.canonical_state, state_goal)
            if path is None:
                await self._park(adapter, portal_app, f"No valid transition from {app.canonical_state.value} to "
                                                      f"{state_goal.value}", app.id, result)
                return
            for step in path:
                # Steps the portal skipped over are inferred from the lifecycle, and marked so in the ledger.
                inferred = {"inferred": step != path[-1], "reported_status": portal_app["status"]}
                try:
                    if step == CanonicalState.SANCTIONED:
                        plan = await adapter.get_payments(self.sources, portal_app["app_id"])
                        if plan:
                            await self.ledger.sanction(app, [(p["description"], Decimal(str(p["amount"])))
                                                             for p in plan], actor)
                        else:
                            await self.ledger.transition(app, step, actor, {"source_ref": portal_app["app_id"],
                                                                            **inferred}, adapter.source)
                    else:
                        await self.ledger.transition(app, step, actor, {"source_ref": portal_app["app_id"],
                                                                        "source_status": portal_app["status"],
                                                                        **inferred}, adapter.source)
                    result.transitions += 1
                except LedgerError as exc:
                    await self._park(adapter, portal_app, exc.detail, app.id, result)
                    return
        if target in PAYMENT_DRIVEN or app.canonical_state in PAYMENT_DRIVEN | {CanonicalState.SANCTIONED}:
            await self._sync_payments(adapter, app, portal_app, result)

    async def _sync_payments(self, adapter: PortalAdapter, app: Application, portal_app: dict,
                             result: SyncResult) -> None:
        actor = f"source:{adapter.source.value}"
        payments = {p.instalment: p for p in (await self.db.execute(
            select(Payment).where(Payment.application_id == app.id))).scalars()}
        for remote in await adapter.get_payments(self.sources, portal_app["app_id"]):
            wanted = adapter.map.payment_state(remote.get("status", ""))
            local = payments.get(remote["instalment"])
            if local is None:
                await self._park(adapter, {**portal_app, "status": remote.get("status", "")},
                                 f"The portal reports instalment {remote.get('instalment')} "
                                 f"(₹{remote.get('amount')}), which is not in the sanctioned plan", app.id, result)
                continue
            if wanted is None:
                if remote.get("status") not in (None, "", "SCHEDULED"):
                    await self._park(adapter, {**portal_app, "status": remote["status"]},
                                     f"Unknown payment status {remote['status']!r}", app.id, result)
                continue
            for step in PAYMENT_PATHS.get(wanted, []):
                if local.state == step or (step == PaymentState.INITIATED and local.state != PaymentState.SCHEDULED):
                    continue
                try:
                    await self.ledger.update_payment(app, local.id, step, actor, pfms_ref=remote.get("txn_ref"),
                                                     failure_code=remote.get("failure_code"), source=adapter.source)
                    result.payments_updated += 1
                except LedgerError as exc:
                    await self._park(adapter, {**portal_app, "status": remote.get("status", "")}, exc.detail,
                                     app.id, result)
                    break

    async def sync_all(self) -> list[SyncResult]:
        students = (await self.db.execute(select(Student).where(Student.aadhaar_ref_token.is_not(None)))).scalars().all()
        results = []
        for s in students:
            student_id = s.id
            try:
                results.append(await self.sync_student(s))
            except Exception as exc:  # noqa: BLE001 - one student's failure never stops the others
                logger.exception("portal sync failed for %s", student_id)
                await self.db.rollback()
                results.append(SyncResult(student_id=student_id, errors=[f"{type(exc).__name__}: {exc}"]))
        return results
