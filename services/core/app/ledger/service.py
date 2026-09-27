"""Scholarship Ledger: event-sourced history + current-state rows in Postgres (ARCHITECTURE.md §6.3).

Every change appends a hash-chained event and updates the current-state row in the same
transaction, and queues the event in the outbox for NATS. Read models are SQL projections over
those rows. Methods flush but never commit: the caller owns the unit of work.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.ledger.models import Application, Deficiency, Household, LedgerEvent, Payment
from app.shared.events import emit
from app.shared.hashing import GENESIS, event_hash
from app.shared.ids import new_id
from app.shared.types import CanonicalState, PaymentState, SchemeType, SourceSystem
from app.students.models import Student

SCHEME_CODES = {SchemeType.PRE_MATRIC: "PRM", SchemeType.POST_MATRIC: "PM", SchemeType.TOP_CLASS: "TC",
                SchemeType.NFST: "NFST", SchemeType.NOS: "NOS"}

VALID_TRANSITIONS: dict[CanonicalState, set[CanonicalState]] = {
    CanonicalState.DRAFT: {CanonicalState.SUBMITTED},
    CanonicalState.SUBMITTED: {CanonicalState.INSTITUTE_VERIFICATION},
    CanonicalState.INSTITUTE_VERIFICATION: {CanonicalState.DEFICIENCY_RAISED, CanonicalState.AUTHORITY_VERIFICATION},
    CanonicalState.DEFICIENCY_RAISED: {CanonicalState.RESUBMITTED},
    CanonicalState.RESUBMITTED: {CanonicalState.INSTITUTE_VERIFICATION},
    CanonicalState.AUTHORITY_VERIFICATION: {CanonicalState.DEFICIENCY_RAISED, CanonicalState.SANCTIONED,
                                            CanonicalState.REJECTED},
    CanonicalState.SANCTIONED: {CanonicalState.PAYMENT_INITIATED},
    CanonicalState.PAYMENT_INITIATED: {CanonicalState.CREDITED, CanonicalState.PAYMENT_FAILED},
    CanonicalState.PAYMENT_FAILED: {CanonicalState.PAYMENT_INITIATED},
    CanonicalState.CREDITED: {CanonicalState.RENEWAL_DUE, CanonicalState.PAYMENT_INITIATED},  # next instalment
    CanonicalState.RENEWAL_DUE: {CanonicalState.SUBMITTED},
    CanonicalState.REJECTED: set(),
}

STATE_EVENT = {
    CanonicalState.SUBMITTED: "ApplicationSubmitted",
    CanonicalState.INSTITUTE_VERIFICATION: "InstituteVerificationStarted",
    CanonicalState.DEFICIENCY_RAISED: "DeficiencyRaised",
    CanonicalState.RESUBMITTED: "Resubmitted",
    CanonicalState.AUTHORITY_VERIFICATION: "AuthorityVerificationStarted",
    CanonicalState.SANCTIONED: "Sanctioned",
    CanonicalState.REJECTED: "Rejected",
    CanonicalState.PAYMENT_INITIATED: "PaymentInitiated",
    CanonicalState.CREDITED: "PaymentCredited",
    CanonicalState.PAYMENT_FAILED: "PaymentFailed",
    CanonicalState.RENEWAL_DUE: "RenewalDue",
}

# States that count as "currently holding" a scholarship for the one-scheme rule.
HOLDING_STATES = {CanonicalState.SANCTIONED, CanonicalState.PAYMENT_INITIATED, CanonicalState.PAYMENT_FAILED,
                  CanonicalState.CREDITED}

NEXT_ACTION = {
    CanonicalState.DRAFT: "Review the pre-filled application and submit it",
    CanonicalState.SUBMITTED: "Waiting for your institute to start verification",
    CanonicalState.INSTITUTE_VERIFICATION: "Your institute is verifying your application",
    CanonicalState.RESUBMITTED: "Waiting for your institute to re-check your response",
    CanonicalState.AUTHORITY_VERIFICATION: "The district/state authority is verifying your application",
    CanonicalState.SANCTIONED: "Sanctioned: the payment will be sent to your bank account",
    CanonicalState.PAYMENT_INITIATED: "Payment has been sent to PFMS for transfer to your bank account",
    CanonicalState.CREDITED: None,
    CanonicalState.RENEWAL_DUE: "Renew your scholarship for the next academic year",
    CanonicalState.REJECTED: "Application rejected: contact your institute's scholarship cell",
}


def subject_for(event_type: str) -> str:
    if event_type == "SLABreached":
        return "sla.breached"
    if event_type.startswith("Deficiency"):
        return f"deficiency.{event_type}"
    if event_type.startswith("Payment"):
        return f"payment.{event_type}"
    if event_type.startswith("Review"):
        return f"verification.{event_type}"
    return f"application.{event_type}"


class LedgerError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class ChainCheck:
    application_id: str
    valid: bool
    events_checked: int
    first_invalid_event_id: Optional[str] = None
    reason: Optional[str] = None


def _aware(dt: datetime) -> datetime:
    """Timezone-aware UTC. Event times are hashed, and Postgres returns them in UTC, so a time given in
    another offset (e.g. a portal's +05:30) must be normalised before hashing or the chain will not verify."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def money(value: Decimal) -> float:
    return float(round(value, 2))


class LedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── queries ─────────────────────────────────────────────

    async def get_application(self, application_id: str) -> Optional[Application]:
        return await self.db.get(Application, application_id)

    async def require_application(self, application_id: str) -> Application:
        app = await self.get_application(application_id)
        if app is None:
            raise LedgerError(404, "Application not found")
        return app

    async def applications_for(self, student_id: str) -> list[Application]:
        return list((await self.db.execute(
            select(Application).where(Application.student_id == student_id).order_by(Application.created_at)
        )).scalars())

    async def timeline(self, application_id: str) -> list[LedgerEvent]:
        return list((await self.db.execute(
            select(LedgerEvent).where(LedgerEvent.application_id == application_id).order_by(LedgerEvent.sequence_no)
        )).scalars())

    async def events_since(self, student_id: str, position: int, limit: int = 500) -> list[LedgerEvent]:
        return list((await self.db.execute(
            select(LedgerEvent).where(LedgerEvent.student_id == student_id, LedgerEvent.position > position)
            .order_by(LedgerEvent.position).limit(limit)
        )).scalars())

    # ── writes ──────────────────────────────────────────────

    async def append_event(self, app: Application, event_type: str, payload: dict[str, Any], actor: str,
                           source: SourceSystem = SourceSystem.SCHOLARSETU,
                           occurred_at: Optional[datetime] = None) -> LedgerEvent:
        """Append to the application's hash chain. The row lock serialises concurrent appends."""
        await self.db.execute(select(Application.id).where(Application.id == app.id).with_for_update())
        last = (await self.db.execute(
            select(LedgerEvent.sequence_no, LedgerEvent.hash).where(LedgerEvent.application_id == app.id)
            .order_by(LedgerEvent.sequence_no.desc()).limit(1)
        )).first()
        sequence_no, hash_prev = (last[0] + 1, last[1]) if last else (1, GENESIS)
        event_id = new_id()
        occurred_at = _aware(occurred_at) if occurred_at else datetime.now(timezone.utc)
        event = LedgerEvent(
            event_id=event_id, application_id=app.id, sequence_no=sequence_no, student_id=app.student_id,
            type=event_type, scheme=app.scheme, source=source, actor=actor, occurred_at=occurred_at, payload=payload,
            hash_prev=hash_prev, hash=event_hash(event_id, event_type, app.id, occurred_at, payload, hash_prev),
        )
        self.db.add(event)
        await emit(self.db, subject_for(event_type), event_type,
                   {"application_id": app.id, "student_id": app.student_id, "scheme": app.scheme.value,
                    "sequence_no": sequence_no, "actor": actor, **payload},
                   correlation_id=app.id, message_id=event_id)
        await self.db.flush()
        return event

    async def create_application(self, student_id: str, scheme: SchemeType, academic_year: str, actor: str,
                                 details: Optional[dict[str, Any]] = None,
                                 initial_state: CanonicalState = CanonicalState.SUBMITTED,
                                 source_system: SourceSystem = SourceSystem.SCHOLARSETU,
                                 source_ref: Optional[str] = None,
                                 occurred_at: Optional[datetime] = None) -> Application:
        if initial_state not in (CanonicalState.DRAFT, CanonicalState.SUBMITTED):
            raise LedgerError(422, "New applications start as DRAFT or SUBMITTED")
        if await self.db.get(Student, student_id) is None:
            raise LedgerError(404, f"Student {student_id} not found")
        seq = await self.db.scalar(select(func.nextval("application_seq")))
        occurred_at = _aware(occurred_at) if occurred_at else datetime.now(timezone.utc)
        app = Application(
            id=f"APP-{SCHEME_CODES[scheme]}-{academic_year[:4]}-{seq:06d}", seq=seq, student_id=student_id,
            scheme=scheme, academic_year=academic_year, source_system=source_system, source_ref=source_ref,
            canonical_state=initial_state, state_changed_at=occurred_at, details=details or {},
        )
        self.db.add(app)
        await self.db.flush()
        await self.append_event(app, "ApplicationCreated",
                                {"scheme": scheme.value, "academic_year": academic_year,
                                 "initial_state": initial_state.value, "source_ref": source_ref,
                                 "details": details or {}},
                                actor, source_system, occurred_at)
        return app

    async def transition(self, app: Application, new_state: CanonicalState, actor: str,
                         payload: Optional[dict[str, Any]] = None, source: SourceSystem = SourceSystem.SCHOLARSETU,
                         occurred_at: Optional[datetime] = None) -> LedgerEvent:
        current = app.canonical_state
        if new_state not in VALID_TRANSITIONS.get(current, set()):
            raise LedgerError(409, f"Invalid transition from {current.value} to {new_state.value}")
        occurred_at = _aware(occurred_at) if occurred_at else datetime.now(timezone.utc)
        event = await self.append_event(app, STATE_EVENT[new_state],
                                        {"from_state": current.value, "to_state": new_state.value, **(payload or {})},
                                        actor, source, occurred_at)
        app.canonical_state = new_state
        app.state_changed_at = occurred_at
        await self.db.flush()
        return event

    async def raise_deficiency(self, app: Application, code: str, description: str, raised_by_role: str,
                               actor: str, due_days: int = 15, occurred_at: Optional[datetime] = None) -> Deficiency:
        occurred_at = _aware(occurred_at) if occurred_at else datetime.now(timezone.utc)
        deficiency = Deficiency(id=new_id(), application_id=app.id, code=code, description=description,
                                raised_by_role=raised_by_role, raised_at=occurred_at,
                                due_at=occurred_at + timedelta(days=due_days))
        self.db.add(deficiency)
        await self.db.flush()
        await self.transition(app, CanonicalState.DEFICIENCY_RAISED, actor,
                              {"deficiency_id": deficiency.id, "deficiency_code": code, "description": description,
                               "raised_by_role": raised_by_role, "due_at": deficiency.due_at.isoformat()},
                              occurred_at=occurred_at)
        return deficiency

    async def respond_deficiency(self, app: Application, deficiency_id: str, response: dict[str, Any],
                                 actor: str) -> LedgerEvent:
        deficiency = await self.db.get(Deficiency, deficiency_id)
        if deficiency is None or deficiency.application_id != app.id:
            raise LedgerError(404, "Deficiency not found")
        if deficiency.resolved_at is not None:
            raise LedgerError(409, "Deficiency already answered")
        deficiency.resolved_at = datetime.now(timezone.utc)
        deficiency.response = response
        event = await self.append_event(app, "DeficiencyResponded",
                                        {"deficiency_id": deficiency_id, "code": deficiency.code, **response}, actor)
        still_open = await self.db.scalar(select(func.count()).select_from(Deficiency).where(
            Deficiency.application_id == app.id, Deficiency.resolved_at.is_(None)))
        if still_open == 0 and app.canonical_state == CanonicalState.DEFICIENCY_RAISED:
            await self.transition(app, CanonicalState.RESUBMITTED, actor, {"deficiency_id": deficiency_id})
        return event

    async def sanction(self, app: Application, instalments: list[tuple[str, Decimal]], actor: str,
                       occurred_at: Optional[datetime] = None) -> list[Payment]:
        """Sanction with its instalment plan; amounts are recorded once, here, in the ledger."""
        if not instalments:
            raise LedgerError(422, "A sanction needs at least one instalment")
        occurred_at = _aware(occurred_at) if occurred_at else datetime.now(timezone.utc)
        payments = [Payment(id=new_id(), application_id=app.id, instalment=i, description=desc,
                            amount=Decimal(str(amount)), state=PaymentState.SCHEDULED)
                    for i, (desc, amount) in enumerate(instalments, start=1)]
        self.db.add_all(payments)
        await self.db.flush()
        await self.transition(app, CanonicalState.SANCTIONED, actor, {
            "total_amount": money(sum((p.amount for p in payments), Decimal(0))),
            "instalments": [{"payment_id": p.id, "instalment": p.instalment, "description": p.description,
                             "amount": money(p.amount)} for p in payments],
        }, occurred_at=occurred_at)
        return payments

    async def update_payment(self, app: Application, payment_id: str, new_state: PaymentState, actor: str,
                             pfms_ref: Optional[str] = None, failure_code: Optional[str] = None,
                             source: SourceSystem = SourceSystem.SCHOLARSETU,
                             occurred_at: Optional[datetime] = None) -> Payment:
        payment = await self.db.get(Payment, payment_id)
        if payment is None or payment.application_id != app.id:
            raise LedgerError(404, "Payment not found")
        allowed = {PaymentState.SCHEDULED: {PaymentState.INITIATED},
                   PaymentState.INITIATED: {PaymentState.CREDITED, PaymentState.FAILED},
                   PaymentState.FAILED: {PaymentState.RETRYING},
                   PaymentState.RETRYING: {PaymentState.CREDITED, PaymentState.FAILED}}
        if new_state not in allowed.get(payment.state, set()):
            raise LedgerError(409, f"Payment cannot go from {payment.state.value} to {new_state.value}")
        occurred_at = _aware(occurred_at) if occurred_at else datetime.now(timezone.utc)
        payment.state = new_state
        payment.pfms_ref = pfms_ref or payment.pfms_ref
        payment.failure_code = failure_code if new_state == PaymentState.FAILED else None
        if new_state in (PaymentState.INITIATED, PaymentState.RETRYING):
            payment.initiated_at = occurred_at
        if new_state == PaymentState.CREDITED:
            payment.credited_at = occurred_at
        details = {"payment_id": payment.id, "instalment": payment.instalment, "amount": money(payment.amount),
                   "pfms_ref": payment.pfms_ref, "failure_code": payment.failure_code}
        target = {PaymentState.INITIATED: CanonicalState.PAYMENT_INITIATED,
                  PaymentState.RETRYING: CanonicalState.PAYMENT_INITIATED,
                  PaymentState.CREDITED: CanonicalState.CREDITED,
                  PaymentState.FAILED: CanonicalState.PAYMENT_FAILED}[new_state]
        if target in VALID_TRANSITIONS.get(app.canonical_state, set()):
            await self.transition(app, target, actor, details, source, occurred_at)
        else:  # e.g. a second instalment credited while the application is already CREDITED
            await self.append_event(app, STATE_EVENT[target], details, actor, source, occurred_at)
        return payment

    # ── integrity ───────────────────────────────────────────

    async def verify_chain(self, application_id: str) -> ChainCheck:
        """Recompute every hash with the same function used to write it."""
        events = await self.timeline(application_id)
        prev = GENESIS
        for index, e in enumerate(events, start=1):
            if e.sequence_no != index:
                return ChainCheck(application_id, False, index, e.event_id, "sequence gap or reorder")
            if e.hash_prev != prev:
                return ChainCheck(application_id, False, index, e.event_id, "hash_prev does not match previous event")
            expected = event_hash(e.event_id, e.type, e.application_id, _aware(e.occurred_at), e.payload, e.hash_prev)
            if expected != e.hash:
                return ChainCheck(application_id, False, index, e.event_id, "event content does not match its hash")
            prev = e.hash
        return ChainCheck(application_id, True, len(events))

    # ── read models ─────────────────────────────────────────

    async def open_deficiencies(self, application_ids: list[str]) -> list[Deficiency]:
        if not application_ids:
            return []
        return list((await self.db.execute(
            select(Deficiency).where(Deficiency.application_id.in_(application_ids), Deficiency.resolved_at.is_(None))
            .order_by(Deficiency.raised_at)
        )).scalars())

    async def payments_for(self, application_ids: list[str]) -> list[Payment]:
        if not application_ids:
            return []
        return list((await self.db.execute(
            select(Payment).where(Payment.application_id.in_(application_ids))
            .order_by(Payment.application_id, Payment.instalment)
        )).scalars())

    async def student_dashboard(self, student_id: str) -> dict[str, Any]:
        from app.eligibility.service import current_academic_year
        student = await self.db.get(Student, student_id)
        if student is None:
            raise LedgerError(404, f"Student {student_id} not found")
        apps = await self.applications_for(student_id)
        ids = [a.id for a in apps]
        deficiencies = {d.application_id: d for d in await self.open_deficiencies(ids)}
        credited: dict[str, Decimal] = {}
        for p in await self.payments_for(ids):
            if p.state == PaymentState.CREDITED:
                credited[p.application_id] = credited.get(p.application_id, Decimal(0)) + p.amount
        briefs = []
        for a in apps:
            next_action = NEXT_ACTION.get(a.canonical_state)
            if a.id in deficiencies:
                next_action = f"Respond to the deficiency: {deficiencies[a.id].description}"
            if a.canonical_state == CanonicalState.PAYMENT_FAILED:
                next_action = "Payment failed: see the DBT status for the fix steps"
            briefs.append({"id": a.id, "scheme": a.scheme, "academic_year": a.academic_year,
                           "current_state": a.canonical_state, "state_since": _aware(a.state_changed_at),
                           "source_system": a.source_system, "next_action": next_action,
                           "money_received": money(credited.get(a.id, Decimal(0)))})
        return {
            "student": {"id": student.id, "name": student.full_name, "dob": student.dob,
                        "household_id": student.household_id, "district": student.district},
            "applications": briefs,
            "total_received": money(sum(credited.values(), Decimal(0))),
            "current_academic_year": current_academic_year(),
        }

    async def family_dashboard(self, household_id: str) -> dict[str, Any]:
        household = await self.db.get(Household, household_id)
        if household is None:
            raise LedgerError(404, "Household not found")
        members = (await self.db.execute(
            select(Student.id).where(Student.household_id == household_id).order_by(Student.dob)
        )).scalars().all()
        return {"household_id": household_id, "guardian_name": household.guardian_name,
                "students": [await self.student_dashboard(sid) for sid in members]}

    async def money_view(self, student_id: str) -> dict[str, Any]:
        apps = await self.applications_for(student_id)
        by_app: dict[str, list[Payment]] = {}
        for p in await self.payments_for([a.id for a in apps]):
            by_app.setdefault(p.application_id, []).append(p)
        rows = []
        totals = {"sanctioned": Decimal(0), "credited": Decimal(0), "failed": Decimal(0), "pending": Decimal(0)}
        for a in apps:
            payments = by_app.get(a.id, [])
            sums = {"sanctioned": sum((p.amount for p in payments), Decimal(0)),
                    "credited": sum((p.amount for p in payments if p.state == PaymentState.CREDITED), Decimal(0)),
                    "failed": sum((p.amount for p in payments if p.state == PaymentState.FAILED), Decimal(0))}
            sums["pending"] = sums["sanctioned"] - sums["credited"] - sums["failed"]
            for k, v in sums.items():
                totals[k] += v
            rows.append({"application_id": a.id, "scheme": a.scheme, "academic_year": a.academic_year,
                         "state": a.canonical_state, **{k: money(v) for k, v in sums.items()},
                         "instalments": [{"payment_id": p.id, "instalment": p.instalment,
                                          "description": p.description, "amount": money(p.amount),
                                          "state": p.state, "failure_code": p.failure_code,
                                          "initiated_at": p.initiated_at, "credited_at": p.credited_at}
                                         for p in payments]})
        return {"student_id": student_id, **{f"total_{k}": money(v) for k, v in totals.items()},
                "applications": rows}

    async def pending_actions(self, student_id: str) -> list[dict[str, Any]]:
        from app.attestation.models import Attestation
        from app.shared.types import AttestationStatus, ReviewCaseStatus
        from app.verification.models import ReviewCase

        apps = await self.applications_for(student_id)
        actions: list[dict[str, Any]] = []
        for d in await self.open_deficiencies([a.id for a in apps]):
            actions.append({"type": "DEFICIENCY", "application_id": d.application_id, "reference_id": d.id,
                            "description": d.description, "deadline": d.due_at,
                            "action_url": f"/v1/applications/{d.application_id}/deficiencies/{d.id}/respond"})
        info_requested = (await self.db.execute(select(ReviewCase).where(
            ReviewCase.student_id == student_id, ReviewCase.status == ReviewCaseStatus.INFO_REQUESTED))).scalars()
        for case in info_requested:
            actions.append({"type": "REVIEW_INFO_REQUESTED", "application_id": case.application_id,
                            "reference_id": case.id,
                            "description": f"An officer needs more information about your {case.claim_type.value}: "
                                           f"{case.notes or 'see the officer note'}",
                            "deadline": case.sla_deadline, "action_url": None})
        now = datetime.now(timezone.utc)
        soon = now + timedelta(days=settings.ATTESTATION_EXPIRY_WARNING_DAYS)
        attestations = (await self.db.execute(select(Attestation).where(
            Attestation.student_id == student_id, Attestation.status == AttestationStatus.ACTIVE,
            Attestation.valid_until.is_not(None)))).scalars()
        for att in attestations:
            valid_until = _aware(att.valid_until)
            if valid_until <= soon:
                state = "has expired" if valid_until <= now else "expires soon"
                actions.append({"type": "ATTESTATION_EXPIRING", "application_id": None, "reference_id": att.id,
                                "description": f"Your {att.claim_type.value} verification {state} "
                                               f"({valid_until.date()}). Renew it to avoid delays.",
                                "deadline": valid_until, "action_url": "/v1/verify/claims"})
        return actions

    async def sla_monitor(self) -> list[dict[str, Any]]:
        """Open applications with time in their current state against the configured SLA."""
        now = datetime.now(timezone.utc)
        limits = settings.sla_days
        apps = (await self.db.execute(
            select(Application, Student.district, Student.state).join(Student, Student.id == Application.student_id)
            .where(Application.canonical_state.in_(list(limits)))
        )).all()
        rows = []
        for app, district, state in apps:
            limit = (settings.sla_seconds(app.canonical_state) or 0) / 86400  # same clock as the SLA workflow
            days = (now - _aware(app.state_changed_at)).total_seconds() / 86400
            rows.append({"application_id": app.id, "scheme": app.scheme, "state": app.canonical_state,
                         "district": district, "state_name": state, "days_in_state": round(days, 1),
                         "sla_days": round(limit, 4), "breached": days > limit})
        return sorted(rows, key=lambda r: r["days_in_state"] - r["sla_days"], reverse=True)


def get_ledger_service(db: AsyncSession = Depends(get_db)) -> LedgerService:
    return LedgerService(db)
