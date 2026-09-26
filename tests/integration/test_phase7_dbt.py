"""Phase 7: DBT Guardian checks against (mock) PFMS/NPCI and guides fixes; never passes blind."""

from decimal import Decimal

from sqlalchemy import select

from app.dbt_guardian.models import DbtRetry
from app.dbt_guardian.service import DBTGuardianService
from app.ledger.models import Application, OutboxMessage
from app.ledger.service import LedgerService
from app.nudge.models import Notification
from app.nudge.service import NudgeService
from app.shared.events import BaseEvent
from app.shared.types import PaymentState
from app.verification.sources import SourceClient
from tests.conftest import mocks_data


async def test_scene4_sunita_is_not_aadhaar_seeded(client, demo, users, gov):
    r = await client.post(f"/v1/dbt/health-check/{demo['sunita_application']}", headers=await users.headers("sunita"))
    assert r.status_code == 200
    body = r.json()
    checks = {c["code"]: c["status"] for c in body["checks"]}
    assert body["overall_status"] == "FAIL"
    assert checks == {"AADHAAR_SEEDED": "FAIL", "ACCOUNT_ACTIVE": "PASS", "NAME_MATCH": "PASS", "ACCOUNT_TYPE": "PASS"}
    issue = body["issues"][0]
    assert issue["code"] == "AADHAAR_NOT_SEEDED"
    assert "आधार" in issue["message_hi"] and len(issue["fix_steps_hi"]) >= 3 and "DBT" in issue["fix_steps"][1]


async def test_seeded_account_passes(client, demo, users, gov):
    body = (await client.post(f"/v1/dbt/health-check/{demo['rahul_application']}",
                              headers=await users.headers("district"))).json()
    assert body["overall_status"] == "PASS" and body["issues"] == []


async def test_name_mismatch_is_caught(client, demo, users, gov):
    mocks_data.BANK_ACCOUNTS["AREF-JH-0009914"]["holder_name"] = "RAKESH MURMU"
    body = (await client.post(f"/v1/dbt/health-check/{demo['rahul_application']}",
                              headers=await users.headers("rahul"))).json()
    assert body["overall_status"] == "FAIL" and [i["code"] for i in body["issues"]] == ["NAME_MISMATCH"]


async def test_pfms_down_is_unavailable_not_pass(client, demo, users, gov):
    gov.down.add("/pfms")
    body = (await client.post(f"/v1/dbt/health-check/{demo['rahul_application']}",
                              headers=await users.headers("rahul"))).json()
    assert body["overall_status"] == "UNAVAILABLE"


async def test_status_endpoint_explains_failed_payments(client, db, demo, users, gov):
    ledger = LedgerService(db)
    app = await db.get(Application, demo["sunita_application"])
    [payment] = await ledger.sanction(app, [("Maintenance allowance", Decimal("5000"))], "system:test")
    await ledger.update_payment(app, payment.id, PaymentState.INITIATED, "system:test", pfms_ref="PFMS-1")
    await ledger.update_payment(app, payment.id, PaymentState.FAILED, "system:test", failure_code="AADHAAR_NOT_SEEDED")
    await db.commit()
    r = await client.get(f"/v1/dbt/status/{demo['sunita_application']}", headers=await users.headers("sunita"))
    assert r.status_code == 200
    [p] = r.json()["payments"]
    assert p["state"] == "FAILED" and p["guidance"]["code"] == "AADHAAR_NOT_SEEDED" and p["guidance"]["fix_steps_hi"]


async def test_retry_is_blocked_until_fixed_then_credited(client, db, demo, users, gov):
    ledger = LedgerService(db)
    app = await db.get(Application, demo["sunita_application"])
    [payment] = await ledger.sanction(app, [("Maintenance allowance", Decimal("5000"))], "system:test")
    await ledger.update_payment(app, payment.id, PaymentState.INITIATED, "system:test", pfms_ref="PFMS-1")
    await ledger.update_payment(app, payment.id, PaymentState.FAILED, "system:test", failure_code="AADHAAR_NOT_SEEDED")
    await db.commit()
    url = f"/v1/dbt/applications/{app.id}/payments/{payment.id}/retry"
    sunita = await users.headers("sunita")

    blocked = await client.post(url, headers=sunita, json={"confirm_fixed": True})
    assert blocked.status_code == 200 and blocked.json()["status"] == "BLOCKED"
    assert blocked.json()["issues"][0]["code"] == "AADHAAR_NOT_SEEDED"

    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True  # the student got seeded at the bank
    submitted = await client.post(url, headers=sunita, json={"confirm_fixed": True})
    assert submitted.json()["status"] == "SUBMITTED" and submitted.json()["pfms_ref"].startswith("PFMS-")

    db.expire_all()
    retry = await db.get(DbtRetry, submitted.json()["id"])
    client_ = SourceClient("http://mocks", transport=gov.transport)
    await DBTGuardianService(db, client_).settle_retry(retry, "system:test")
    await db.commit()
    await client_.aclose()
    money = (await client.get("/v1/me/payments", headers=sunita)).json()
    assert money["total_credited"] == 5000 and money["applications"][0]["state"] == "CREDITED"


async def test_failed_health_check_alerts_the_student_by_sms(client, db, demo, users, gov):
    await client.post(f"/v1/dbt/health-check/{demo['sunita_application']}", headers=await users.headers("sunita"))
    message = (await db.execute(select(OutboxMessage).where(OutboxMessage.event_type == "DBTHealthChecked"))).scalar_one()
    assert await NudgeService(db).handle_event(BaseEvent(**message.payload)) >= 2
    channels = {n.channel.value for n in (await db.execute(select(Notification))).scalars()}
    assert channels == {"PUSH", "SMS"}
