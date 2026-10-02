"""Phase 8: SLA and DBT-retry workflows (Temporal, time-skipping), breach notifications, SMS and IVR."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from app.config import settings
from app.dbt_guardian.models import DbtRetry
from app.ledger.models import Application, LedgerEvent, OutboxMessage
from app.ledger.service import LedgerService
from app.nudge.models import Notification
from app.nudge.service import NudgeService
from app.shared.events import BaseEvent
from app.shared.types import CanonicalState, PaymentState
from app.workflows import activities as acts
from app.workflows.definitions import DBTRetryWorkflow, SLAWorkflow
from app.workflows.worker import ACTIVITIES
from tests.conftest import PHONES, mocks_data


@pytest.fixture(scope="module")
async def temporal():
    env = await WorkflowEnvironment.start_time_skipping()
    yield env
    await env.shutdown()


async def _run_worker(env, fn):
    queue = f"test-{uuid.uuid4()}"
    async with Worker(env.client, task_queue=queue, workflows=[SLAWorkflow, DBTRetryWorkflow], activities=ACTIVITIES):
        return await fn(queue)


async def _sla_events(db, app_id):
    db.expire_all()
    return (await db.execute(select(LedgerEvent).where(LedgerEvent.application_id == app_id,
                                                       LedgerEvent.type == "SLABreached")
                             .order_by(LedgerEvent.sequence_no))).scalars().all()


# ── SLA ───────────────────────────────────────────────────────────────────────


async def test_breach_is_recorded_only_while_still_stuck(db, demo, monkeypatch):
    monkeypatch.setattr(settings, "SLA_DAYS_AUTHORITY_VERIFICATION", 5)  # Sunita has waited 9 days
    snap = await acts.sla_snapshot(demo["sunita_application"])
    result = await acts.record_sla_breach(demo["sunita_application"], snap["state"], snap["state_changed_at"], 0)
    # Authority verification is the district's stage, so the first reminder goes to the district officer.
    assert result["breached"] and result["escalated_to"] == "DISTRICT_OFFICER"
    stale = await acts.record_sla_breach(demo["sunita_application"], "SUBMITTED", snap["state_changed_at"], 0)
    assert stale == {"breached": False}
    [event] = await _sla_events(db, demo["sunita_application"])
    assert event.payload["stage"] == "AUTHORITY_VERIFICATION" and event.payload["days_in_stage"] >= 9
    subjects = (await db.execute(select(OutboxMessage.subject).where(OutboxMessage.event_type == "SLABreached"))).scalars().all()
    assert subjects == ["sla.breached"]


async def test_sla_workflow_escalates_up_the_chain_then_stops_when_the_stage_changes(db, demo, temporal, monkeypatch):
    monkeypatch.setattr(settings, "SLA_DAYS_AUTHORITY_VERIFICATION", 5)
    monkeypatch.setattr(settings, "SLA_ESCALATION_DAYS", 2)
    app_id = demo["sunita_application"]

    async def scenario(queue):
        handle = await temporal.client.start_workflow(SLAWorkflow.run, app_id, id=f"sla-{app_id}", task_queue=queue)
        await temporal.sleep(timedelta(days=5))  # enough for tier 0 and +2d tier 1 (and more idle time)
        tiers = [e.payload["escalated_to"] for e in await _sla_events(db, app_id)]
        # The officer returns it to the student: DEFICIENCY_RAISED has no officer SLA, so the watch ends.
        app = await db.get(Application, app_id)
        await LedgerService(db).raise_deficiency(app, "INCOME_CERT_EXPIRED", "Upload a current income certificate",
                                                 "DISTRICT_OFFICER", "system:test")
        await db.commit()
        return tiers, await handle.result()

    tiers, outcome = await _run_worker(temporal, scenario)
    assert tiers == ["DISTRICT_OFFICER", "STATE_OFFICER"]  # never repeated, never the institute
    assert outcome == "no SLA for current stage"
    assert len(await _sla_events(db, app_id)) == 2  # no further reminders once the stage changed


async def test_breach_tells_the_student_honestly_and_reminds_the_right_officers(db, demo, monkeypatch):
    monkeypatch.setattr(settings, "SLA_DAYS_AUTHORITY_VERIFICATION", 5)
    snap = await acts.sla_snapshot(demo["sunita_application"])
    await acts.record_sla_breach(demo["sunita_application"], snap["state"], snap["state_changed_at"], 0)
    message = (await db.execute(select(OutboxMessage).where(OutboxMessage.subject == "sla.breached"))).scalar_one()
    await NudgeService(db).handle_event(BaseEvent(**message.payload))
    notes = (await db.execute(select(Notification))).scalars().all()
    student = [n for n in notes if n.template_key == "SLA_BREACH_STUDENT" and n.language == "hi"]
    officer = [n for n in notes if n.template_key == "SLA_BREACH_OFFICER"]
    assert student and "जिला कल्याण अधिकारी" in student[0].body  # "we have reminded the district welfare officer"
    assert "9 दिन" in student[0].body and "5 दिन" in student[0].body  # waited 9 days against a 5-day target
    assert len(officer) == 1 and "Please act on them" in officer[0].body  # only the Dumka district officer
    assert "waiting 9 days against a target of 5 days" in officer[0].body  # officers read English, not the student's Hindi


async def test_officer_reminders_are_one_digest_per_stage_per_day(db, demo, gov, monkeypatch):
    from app.eligibility.service import current_academic_year
    from tests.demo_world import seed_synthetic_population
    monkeypatch.setattr(settings, "SLA_DAYS_SUBMITTED", 0.00001)
    await seed_synthetic_population(db, mocks_data.ENROLLED_ST[:30], current_academic_year())
    submitted = (await db.execute(select(Application.id).where(Application.canonical_state == CanonicalState.SUBMITTED))).scalars().all()
    assert len(submitted) >= 5
    for app_id in submitted:
        snap = await acts.sla_snapshot(app_id)
        await acts.record_sla_breach(app_id, snap["state"], snap["state_changed_at"], 0)
    for message in (await db.execute(select(OutboxMessage).where(OutboxMessage.subject == "sla.breached"))).scalars().all():
        await NudgeService(db).handle_event(BaseEvent(**message.payload))
    officer_notes = (await db.execute(select(Notification).where(Notification.template_key == "SLA_BREACH_OFFICER"))).scalars().all()
    # Two Dumka institute officers, one digest each, counting every breached application.
    assert len(officer_notes) == 2
    assert all(len(n.data["application_ids"]) == len(submitted) and f"{len(submitted)} application(s)" in n.body
               for n in officer_notes)


def test_durations_read_naturally():
    from app.nudge.service import duration
    assert duration(9, "en") == "9 days" and duration(1, "en") == "1 day"
    assert duration(60 / 86400, "en") == "1 minute" and duration(0.125, "hi") == "3 घंटे"


# ── DBT retry ─────────────────────────────────────────────────────────────────


async def test_dbt_retry_workflow_settles_the_payment(client, db, demo, users, gov, temporal):
    ledger = LedgerService(db)
    app = await db.get(Application, demo["sunita_application"])
    [payment] = await ledger.sanction(app, [("Maintenance allowance", Decimal("5000"))], "system:test")
    await ledger.update_payment(app, payment.id, PaymentState.INITIATED, "system:test", pfms_ref="PFMS-1")
    await ledger.update_payment(app, payment.id, PaymentState.FAILED, "system:test", failure_code="AADHAAR_NOT_SEEDED")
    app_id, payment_id = app.id, payment.id
    await db.commit()
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    retry = (await client.post(f"/v1/dbt/applications/{app_id}/payments/{payment_id}/retry",
                               headers=await users.headers("sunita"), json={"confirm_fixed": True})).json()
    assert retry["status"] == "SUBMITTED"

    # The workflow's activity talks to PFMS through MOCK_SERVICE_URL; point it at the in-process mocks.
    import app.workflows.activities as activities_module
    from app.verification.sources import SourceClient
    monkeypatch_client = lambda *_a, **_k: SourceClient("http://mocks", transport=gov.transport)  # noqa: E731
    original = activities_module.SourceClient
    activities_module.SourceClient = monkeypatch_client
    try:
        outcome = await _run_worker(temporal, lambda q: temporal.client.execute_workflow(
            DBTRetryWorkflow.run, retry["id"], id=f"dbt-retry-{retry['id']}", task_queue=q))
    finally:
        activities_module.SourceClient = original
    assert outcome == "CREDITED"
    db.expire_all()
    assert (await db.get(DbtRetry, retry["id"])).status == "CREDITED"
    assert (await db.get(Application, app_id)).canonical_state == CanonicalState.CREDITED


# ── SMS and IVR ───────────────────────────────────────────────────────────────


async def _sms(client, phone, body, token=None):
    return await client.post("/v1/sms/inbound", json={"from_phone": phone, "body": body},
                             headers={"X-SMS-Gateway-Token": token or settings.SMS_GATEWAY_TOKEN})


async def _last_sms(db, phone):
    from app.gateway.models import OutboundSms
    db.expire_all()
    return (await db.execute(select(OutboundSms).where(OutboundSms.to_phone == phone)
                             .order_by(OutboundSms.created_at.desc()))).scalars().first()


async def test_sms_status_from_the_registered_phone(client, db, demo):
    r = await _sms(client, PHONES["sunita"], f"STATUS {demo['sunita_application']}")
    assert r.status_code == 200
    reply = await _last_sms(db, PHONES["sunita"])
    assert demo["sunita_application"] in reply.body and "जिला/राज्य प्राधिकरण" in reply.body


async def test_sms_from_an_unregistered_number_is_rejected(client, db, demo):
    r = await _sms(client, "9000000123", f"STATUS {demo['sunita_application']}")
    assert r.status_code == 403
    assert await _last_sms(db, "9000000123") is None


async def test_sms_cannot_read_someone_elses_application(client, db, demo):
    await _sms(client, PHONES["rahul"], f"STATUS {demo['sunita_application']}")
    reply = await _last_sms(db, PHONES["rahul"])
    assert demo["sunita_application"] not in reply.body


async def test_guardian_can_ask_about_a_child(client, db, demo):
    await _sms(client, PHONES["guardian"], f"STATUS {demo['rahul_application']}")
    assert demo["rahul_application"] in (await _last_sms(db, PHONES["guardian"])).body


async def test_sms_gateway_must_authenticate(client, demo):
    assert (await _sms(client, PHONES["sunita"], "STATUS X", token="wrong" * 10)).status_code == 401


async def test_ivr_is_honestly_not_implemented(client):
    assert (await client.post("/v1/ivr/call")).status_code == 501


async def test_sms_dev_page_only_in_demo_mode(client, demo, monkeypatch):
    assert (await client.get("/v1/dev/sms-outbox")).status_code == 404
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    page = await client.get("/v1/dev/sms-outbox")
    assert page.status_code == 200 and "Simulated SMS outbox" in page.text
