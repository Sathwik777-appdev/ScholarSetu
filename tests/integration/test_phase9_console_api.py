"""Phase 9: the endpoints the officer/ministry console reads, computed from the ledger and scoped by jurisdiction."""

from decimal import Decimal

from app.ledger.models import Application
from app.ledger.service import LedgerService
from app.shared.types import PaymentState, UserRole
from tests.conftest import bearer, login, make_user


async def test_officer_application_list_carries_names_and_days(client, demo, users):
    rows = (await client.get("/v1/applications", headers=await users.headers("district"))).json()
    sunita = next(r for r in rows if r["id"] == demo["sunita_application"])
    assert sunita["student_name"] == "Sunita Hansda" and sunita["district"] == "Dumka"
    assert sunita["canonical_state"] == "AUTHORITY_VERIFICATION" and sunita["days_in_state"] >= 9


async def _overview(client, headers):
    return (await client.get("/v1/analytics/overview", headers=headers)).json()


async def test_overview_totals_come_from_the_ledger(client, db, demo, users):
    ministry = await users.headers("ministry")
    before = await _overview(client, ministry)  # Rahul's seeded, fully credited instalments
    assert Decimal(before["sanctioned_amount"]) == Decimal(before["credited_amount"]) > 0
    ledger = LedgerService(db)
    app = await db.get(Application, demo["sunita_application"])
    [first, second] = await ledger.sanction(app, [("Instalment 1", Decimal("6000")), ("Instalment 2", Decimal("4000"))],
                                            "system:test")
    await ledger.update_payment(app, first.id, PaymentState.INITIATED, "system:test", pfms_ref="PFMS-9")
    await ledger.update_payment(app, first.id, PaymentState.CREDITED, "system:test")
    await ledger.update_payment(app, second.id, PaymentState.INITIATED, "system:test", pfms_ref="PFMS-10")
    await ledger.update_payment(app, second.id, PaymentState.FAILED, "system:test", failure_code="ACCOUNT_CLOSED")
    await db.commit()

    body = await _overview(client, ministry)
    assert body["scope"] == "All India"
    assert body["total_applications"] == 2 and body["total_students"] == 2
    assert Decimal(body["sanctioned_amount"]) - Decimal(before["sanctioned_amount"]) == Decimal("10000")
    assert Decimal(body["credited_amount"]) - Decimal(before["credited_amount"]) == Decimal("6000")
    assert Decimal(body["failed_amount"]) == Decimal("4000") and body["payments_failed"] == 1
    states = {r["key"]: r["count"] for r in body["by_state"]}
    assert sum(states.values()) == 2 and states[(await db.get(Application, demo["sunita_application"])).canonical_state.value] >= 1

    await make_user(db, "9000000052", UserRole.DISTRICT_OFFICER, "DWO Ranchi", jurisdiction=("Jharkhand", "Ranchi"))
    ranchi = (await client.get("/v1/analytics/overview", headers=bearer(await login(client, db, "9000000052")))).json()
    assert ranchi["scope"] == "Ranchi, Jharkhand" and ranchi["total_applications"] == 0
    assert Decimal(ranchi["sanctioned_amount"]) == 0


async def test_overview_is_for_analytics_roles_only(client, users):
    assert (await client.get("/v1/analytics/overview", headers=await users.headers("sunita"))).status_code == 403
    assert (await client.get("/v1/analytics/overview")).status_code == 401


async def test_sla_monitor_uses_the_same_clock_as_the_sla_workflow(client, demo, users, monkeypatch):
    from app.config import settings
    district = await users.headers("district")
    rows = {r["application_id"]: r for r in (await client.get("/v1/analytics/sla", headers=district)).json()}
    assert rows[demo["sunita_application"]]["breached"] is False  # 9 days of a 21-day target
    monkeypatch.setattr(settings, "DEMO_MODE", True)  # every SLA becomes SLA_DEMO_SECONDS, as in the workflow
    rows = {r["application_id"]: r for r in (await client.get("/v1/analytics/sla", headers=district)).json()}
    assert rows[demo["sunita_application"]]["breached"] is True
    overview = (await client.get("/v1/analytics/overview", headers=district)).json()
    assert overview["open_sla_breaches"] >= 1
