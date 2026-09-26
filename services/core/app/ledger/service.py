from datetime import datetime, timezone, timedelta
import json
from typing import Any, Optional, List, Dict

from app.shared.types import CanonicalState, SchemeType, SourceSystem
from app.shared.events import BaseEvent, EventBus, global_event_bus
from app.shared.hashing import compute_hash
from app.ledger.schemas import (
    StudentDashboard, FamilyDashboard, MoneyView, SLAReport, PendingAction,
    TimelineEntry, ApplicationResponse, LedgerEventResponse, StudentResponse, ApplicationBrief
)

VALID_TRANSITIONS: dict[CanonicalState, set[CanonicalState]] = {
    CanonicalState.DRAFT: {CanonicalState.SUBMITTED},
    CanonicalState.SUBMITTED: {CanonicalState.INSTITUTE_VERIFICATION},
    CanonicalState.INSTITUTE_VERIFICATION: {CanonicalState.DEFICIENCY_RAISED, CanonicalState.AUTHORITY_VERIFICATION},
    CanonicalState.DEFICIENCY_RAISED: {CanonicalState.RESUBMITTED},
    CanonicalState.RESUBMITTED: {CanonicalState.INSTITUTE_VERIFICATION},
    CanonicalState.AUTHORITY_VERIFICATION: {CanonicalState.DEFICIENCY_RAISED, CanonicalState.SANCTIONED, CanonicalState.REJECTED},
    CanonicalState.SANCTIONED: {CanonicalState.PAYMENT_INITIATED},
    CanonicalState.PAYMENT_INITIATED: {CanonicalState.CREDITED, CanonicalState.PAYMENT_FAILED},
    CanonicalState.PAYMENT_FAILED: {CanonicalState.PAYMENT_INITIATED},
    CanonicalState.CREDITED: {CanonicalState.RENEWAL_DUE},
    CanonicalState.RENEWAL_DUE: {CanonicalState.SUBMITTED},
}


class TransitionError(Exception):
    pass


class LedgerService:
    """Event-sourced scholarship ledger with hash chain and CQRS projections."""

    def __init__(self, db_session=None, event_bus: Optional[EventBus] = None):
        self.db = db_session
        self.event_bus = event_bus or global_event_bus
        self._events: list[LedgerEventResponse] = []
        self._applications: dict[str, ApplicationResponse] = {}
        self._seed_demo_ledger()

    def _seed_demo_ledger(self):
        """Pre-seed the ledger with Sunita and Rahul Hansda applications & events matching Judge Demo (§14)."""
        now = datetime.now(timezone.utc)

        # 1. Sunita's Application (Post-Matric)
        sunita_app_id = "APP-PM-2026-000812"
        self._applications[sunita_app_id] = ApplicationResponse(
            id=sunita_app_id,
            student_id="stu-sunita-001",
            scheme=SchemeType.POST_MATRIC,
            academic_year="2026-27",
            canonical_state=CanonicalState.AUTHORITY_VERIFICATION,
            source_system=SourceSystem.NSP,
            details={
                "institute_name": "Dumka Government College",
                "course": "Class 11 Science",
                "father_name": "Babulal Hansda",
                "bank_account_masked": "SBIN0001234-XXXX5678"
            }
        )

        # 2. Rahul's Application (Pre-Matric - Already Credited)
        rahul_app_id = "APP-PRM-2025-004192"
        self._applications[rahul_app_id] = ApplicationResponse(
            id=rahul_app_id,
            student_id="stu-rahul-002",
            scheme=SchemeType.PRE_MATRIC,
            academic_year="2025-26",
            canonical_state=CanonicalState.CREDITED,
            source_system=SourceSystem.SCHOLARSETU,
            details={
                "school_name": "Government High School Dumka",
                "class": 9,
                "amount": 7000.0
            }
        )

        # Seed Hash-Chained Events for Sunita's Application
        evt1_time = now - timedelta(days=5)
        evt1_hash = compute_hash("ApplicationSubmitted", sunita_app_id, evt1_time.isoformat(), "{}", "genesis")
        self._events.append(LedgerEventResponse(
            id="evt_01",
            application_id=sunita_app_id,
            event_type="ApplicationSubmitted",
            payload={"channel": "ScholarSetu Flutter Mobile", "mode": "FamilyMode", "reused_attestations": ["ST_STATUS", "IDENTITY"]},
            source=SourceSystem.SCHOLARSETU,
            occurred_at=evt1_time,
            event_hash=evt1_hash
        ))

        evt2_time = now - timedelta(days=4)
        evt2_hash = compute_hash("InstituteVerified", sunita_app_id, evt2_time.isoformat(), "{}", evt1_hash)
        self._events.append(LedgerEventResponse(
            id="evt_02",
            application_id=sunita_app_id,
            event_type="InstituteVerified",
            payload={"verified_by": "Principal, Dumka Govt College", "aishe_code": "C-41290", "enrolment_confirmed": True},
            source=SourceSystem.NSP,
            occurred_at=evt2_time,
            event_hash=evt2_hash
        ))

        evt3_time = now - timedelta(days=2)
        evt3_hash = compute_hash("ProvisionalIdentityMatch", sunita_app_id, evt3_time.isoformat(), "{}", evt2_hash)
        self._events.append(LedgerEventResponse(
            id="evt_03",
            application_id=sunita_app_id,
            event_type="ProvisionalIdentityMatch",
            payload={
                "score": 0.88,
                "note": "Hansda vs Hansdah transliteration difference. Routed to District Officer review without blocking."
            },
            source=SourceSystem.SCHOLARSETU,
            occurred_at=evt3_time,
            event_hash=evt3_hash
        ))

    async def append_event(
        self, application_id: str, event_type: str, payload: dict[str, Any],
        source: SourceSystem, scheme: SchemeType, student_id: str
    ) -> LedgerEventResponse:
        """Append an event to the ledger with hash chain integrity."""
        app_events = [e for e in self._events if e.application_id == application_id]
        prev_hash = app_events[-1].event_hash if app_events else "genesis"

        occurred_at = datetime.now(timezone.utc)
        payload_json = json.dumps(payload, sort_keys=True)

        new_hash = compute_hash(event_type, application_id, occurred_at.isoformat(), payload_json, prev_hash)

        event = LedgerEventResponse(
            id=f"evt_{len(self._events)+1:03d}",
            application_id=application_id,
            event_type=event_type,
            payload=payload,
            source=source,
            occurred_at=occurred_at,
            event_hash=new_hash
        )
        self._events.append(event)

        # Publish to event bus for reactive CQRS updates and nudges
        try:
            await self.event_bus.publish(
                f"ledger.{scheme.value.lower()}.{event_type.lower()}",
                BaseEvent(
                    event_id=event.id,
                    type=event_type,
                    occurred_at=occurred_at.isoformat(),
                    correlation_id=application_id,
                    payload={"student_id": student_id, **payload}
                )
            )
        except Exception:
            pass

        return event

    async def get_timeline(self, application_id: str) -> list[LedgerEventResponse]:
        """Get ordered event timeline for an application."""
        return [e for e in self._events if e.application_id == application_id]

    async def verify_chain(self, application_id: str) -> bool:
        """Verify hash chain integrity for audit."""
        app_events = [e for e in self._events if e.application_id == application_id]
        prev_hash = "genesis"

        for e in app_events:
            payload_json = json.dumps(e.payload, sort_keys=True)
            expected_hash = compute_hash(e.event_type, e.application_id, e.occurred_at.isoformat(), payload_json, prev_hash)
            if expected_hash != e.event_hash:
                return False
            prev_hash = e.event_hash

        return True

    # ── Demo read-model rows. TODO(Phase 4): derive from DB events; seed via scripts/seed_demo.py. ──
    _DEMO_STUDENTS = {
        "stu-sunita-001": {"name": "Sunita Hansda", "aadhaar_ref": "XXXX-XXXX-4912",
                           "dob": datetime(2008, 4, 12, tzinfo=timezone.utc), "household_id": "hh_hansda_001"},
        "stu-rahul-002": {"name": "Rahul Hansda", "aadhaar_ref": "XXXX-XXXX-9914",
                          "dob": datetime(2010, 8, 15, tzinfo=timezone.utc), "household_id": "hh_hansda_001"},
    }
    _DEMO_HOUSEHOLDS = {"hh_hansda_001": {"guardian_name": "Babulal Hansda (Father)",
                                          "student_ids": ["stu-sunita-001", "stu-rahul-002"]}}
    _DEMO_NEXT_ACTION = {
        "APP-PM-2026-000812": "Aadhaar-bank seeding required at branch (DBT Guardian alert)",
        "APP-PRM-2025-004192": "Renewal due for Class 10 next academic session",
    }
    _DEMO_RECEIVED = {"APP-PRM-2025-004192": 7000.0}
    _DEMO_MONEY = {
        "stu-sunita-001": {
            "application_id": "APP-PM-2026-000812", "sanctioned": 14500.0, "credited": 0.0, "failed": 0.0,
            "pending": 14500.0,
            "instalments": [
                {"instalment_no": 1, "type": "Maintenance Allowance", "amount": 7500.0,
                 "status": "PAYMENT_INITIATED", "date": "2026-09-22"},
                {"instalment_no": 2, "type": "Tuition & Compulsory Fees", "amount": 7000.0,
                 "status": "SANCTIONED", "date": "2026-10-15"},
            ],
        },
    }

    def get_application(self, application_id: str) -> Optional[ApplicationResponse]:
        return self._applications.get(application_id)

    def register_application(self, app: ApplicationResponse) -> None:
        self._applications[app.id] = app

    async def get_student_dashboard(self, student_id: str) -> StudentDashboard:
        """CQRS read model: the student's own applications with current state and next action."""
        profile = self._DEMO_STUDENTS.get(student_id)
        if profile is None:
            raise LookupError(f"No student record for {student_id}")
        apps = [a for a in self._applications.values() if a.student_id == student_id]
        briefs = [
            ApplicationBrief(
                id=a.id, scheme=a.scheme, academic_year=a.academic_year, current_state=a.canonical_state,
                next_action=self._DEMO_NEXT_ACTION.get(a.id), money_received=self._DEMO_RECEIVED.get(a.id, 0.0),
            )
            for a in apps
        ]
        return StudentDashboard(
            student=StudentResponse(id=student_id, name=profile["name"], aadhaar_ref=profile["aadhaar_ref"],
                                    dob=profile["dob"], household_id=profile["household_id"]),
            applications=briefs,
            total_received=sum(b.money_received for b in briefs),
        )

    async def get_family_dashboard(self, household_id: str) -> FamilyDashboard:
        """CQRS read model: every child in the household."""
        household = self._DEMO_HOUSEHOLDS.get(household_id)
        if household is None:
            raise LookupError(f"No household {household_id}")
        return FamilyDashboard(
            household_id=household_id,
            guardian_name=household["guardian_name"],
            students=[await self.get_student_dashboard(sid) for sid in household["student_ids"]],
        )

    async def get_money_view(self, student_id: str) -> MoneyView:
        """CQRS read model: sanctioned vs credited per instalment."""
        money = self._DEMO_MONEY.get(student_id)
        if money is None:
            raise LookupError(f"No payment records for {student_id}")
        return MoneyView(**money)

    async def get_sla_report(self, filters: dict) -> SLAReport:
        """CQRS read model: time spent in each state, breaches."""
        return SLAReport(
            total_applications=1420,
            avg_processing_days=11.4,
            breaches_count=42,
            state_durations={
                "INSTITUTE_VERIFICATION": 4.2,
                "AUTHORITY_VERIFICATION": 6.8,
                "PAYMENT_PROCESSING": 2.1
            }
        )

    async def get_pending_actions(self, student_id: str) -> list[PendingAction]:
        """Deficiencies, expiring attestations, DBT seeding alerts."""
        if student_id != "stu-sunita-001":
            return []
        now = datetime.now(timezone.utc)
        return [
            PendingAction(
                type="DBT_AADHAAR_SEEDING",
                description="Your bank account is not seeded with Aadhaar for DBT. Visit your bank branch with Aadhaar to enable payments.",
                deadline=now + timedelta(days=7),
                action_url="/v1/dbt/status/APP-PM-2026-000812"
            ),
            PendingAction(
                type="INCOME_RENEWAL",
                description="Your previous income certificate has expired. A fresh certificate for FY 2026-27 is required.",
                deadline=now + timedelta(days=14),
                action_url="/v1/verify/claims"
            )
        ]

    async def transition_state(
        self, application_id: str, new_state: CanonicalState, payload: dict[str, Any], source: SourceSystem
    ) -> ApplicationResponse:
        """Validate state transition and update canonical state."""
        app = self._applications.get(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")

        current_state = app.canonical_state
        allowed = VALID_TRANSITIONS.get(current_state, set())

        if new_state not in allowed:
            raise TransitionError(f"Invalid transition from {current_state} to {new_state}")

        await self.append_event(
            application_id=application_id,
            event_type="StateTransition",
            payload={"old_state": current_state.value, "new_state": new_state.value, **payload},
            source=source,
            scheme=app.scheme,
            student_id=app.student_id
        )

        app.canonical_state = new_state
        return app


global_ledger_service = LedgerService()


def get_ledger_service() -> LedgerService:
    return global_ledger_service
