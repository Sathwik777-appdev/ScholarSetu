"""Phase 10: offline delta sync (GET /v1/sync) and the idempotent outbox (POST /v1/sync/outbox)."""

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.ledger.models import Application, Deficiency, LedgerEvent
from app.ledger.service import LedgerService
from app.nudge.models import Notification
from tests.conftest import PHONES, latest_sms_code


@pytest.fixture(autouse=True)
def no_settle(monkeypatch):
    monkeypatch.setattr(settings, "SYNC_SETTLE_SECONDS", 0)


async def _pull(client, headers, cursor=0, limit=200):
    r = await client.get("/v1/sync", headers=headers, params={"cursor": cursor, "limit": limit})
    assert r.status_code == 200, r.text
    return r.json()


async def _push(client, headers, *items):
    r = await client.post("/v1/sync/outbox", headers=headers, json={"items": list(items)})
    assert r.status_code == 200, r.text
    return r.json()["results"]


async def _deficiency(db, app_id) -> str:
    app = await db.get(Application, app_id)
    await LedgerService(db).raise_deficiency(app, "INCOME_CERT_EXPIRED", "Upload a current income certificate",
                                             "DISTRICT_OFFICER", "system:test")
    await db.commit()
    return (await db.execute(select(Deficiency.id).where(Deficiency.application_id == app_id))).scalar_one()


# ── pull ──────────────────────────────────────────────────────────────────────


async def test_pull_returns_only_your_events_in_order_and_pages_by_cursor(client, db, demo, users):
    sunita = await users.headers("sunita")
    page = await _pull(client, sunita)
    assert page["events"] and {e["application_id"] for e in page["events"]} == {demo["sunita_application"]}
    positions = [e["position"] for e in page["events"]]
    assert positions == sorted(positions) and page["next_cursor"] == positions[-1] and not page["has_more"]
    assert [a["id"] for a in page["applications"]] == [demo["sunita_application"]]
    assert page["applications"][0]["canonical_state"] == "AUTHORITY_VERIFICATION"

    first = await _pull(client, sunita, limit=2)
    assert first["has_more"] and len(first["events"]) == 2
    rest = await _pull(client, sunita, cursor=first["next_cursor"])
    assert [e["event_id"] for e in first["events"] + rest["events"]] == [e["event_id"] for e in page["events"]]

    # Nothing new: an empty page that keeps the cursor.
    empty = await _pull(client, sunita, cursor=page["next_cursor"])
    assert empty["events"] == [] and empty["next_cursor"] == page["next_cursor"]

    # A new event shows up after the cursor.
    await _deficiency(db, demo["sunita_application"])
    new = await _pull(client, sunita, cursor=page["next_cursor"])
    assert [e["type"] for e in new["events"]] == ["DeficiencyRaised"]
    assert new["applications"][0]["canonical_state"] == "DEFICIENCY_RAISED"


async def test_guardian_pulls_the_households_children(client, demo, users):
    page = await _pull(client, await users.headers("guardian"))
    assert {e["application_id"] for e in page["events"]} == {demo["sunita_application"], demo["rahul_application"]}


async def test_fresh_events_wait_for_the_settle_window(client, db, demo, users, monkeypatch):
    sunita = await users.headers("sunita")
    cursor = (await _pull(client, sunita))["next_cursor"]
    await _deficiency(db, demo["sunita_application"])
    monkeypatch.setattr(settings, "SYNC_SETTLE_SECONDS", 60)
    held = await _pull(client, sunita, cursor=cursor)
    assert held["events"] == [] and held["next_cursor"] == cursor  # not skipped: served once settled


async def test_officers_and_anonymous_callers_cannot_pull(client, users):
    assert (await client.get("/v1/sync", headers=await users.headers("district"))).status_code == 403
    assert (await client.get("/v1/sync")).status_code == 401


# ── outbox ────────────────────────────────────────────────────────────────────


async def test_offline_deficiency_response_is_applied_exactly_once(client, db, demo, users):
    app_id = demo["sunita_application"]
    deficiency_id = await _deficiency(db, app_id)
    item = {"idempotency_key": "dev1-0001-respond", "action": "RESPOND_DEFICIENCY",
            "payload": {"application_id": app_id, "deficiency_id": deficiency_id,
                        "response_text": "Uploaded the 2026-27 income certificate"}}
    sunita = await users.headers("sunita")
    [first] = await _push(client, sunita, item)
    assert first["status"] == "APPLIED" and first["result"]["type"] == "DeficiencyResponded"
    [again] = await _push(client, sunita, item)  # the phone lost the response and resends
    assert again["status"] == "DUPLICATE" and again["original_status"] == "APPLIED"
    assert again["result"]["event_id"] == first["result"]["event_id"]
    count = await db.scalar(select(func.count()).select_from(LedgerEvent)
                            .where(LedgerEvent.application_id == app_id, LedgerEvent.type == "DeficiencyResponded"))
    assert count == 1
    db.expire_all()
    assert (await db.get(Application, app_id)).canonical_state.value == "RESUBMITTED"


async def test_a_refused_item_does_not_block_the_rest_and_stays_refused(client, db, demo, users):
    rahul = await users.headers("rahul")
    from app.gateway.models import User
    rahul_id = (await db.execute(select(User.id).where(User.phone == PHONES["rahul"]))).scalar_one()
    notification = Notification(user_id=rahul_id, student_id="stu-rahul-002", event_id="evt-test",
                                template_key="TEST", channel="PUSH", language="hi", body="test", data={})
    db.add(notification)
    await db.commit()
    notification_id = notification.id
    steal = {"idempotency_key": "dev2-0001-steal", "action": "SUBMIT_APPLICATION",
             "payload": {"application_id": demo["sunita_application"]}}
    read = {"idempotency_key": "dev2-0002-read", "action": "MARK_NOTIFICATION_READ",
            "payload": {"notification_id": notification_id}}
    bad = {"idempotency_key": "dev2-0003-bad", "action": "CREATE_APPLICATION", "payload": {"scheme": "NOPE"}}
    results = await _push(client, rahul, steal, read, bad)
    assert [r["status"] for r in results] == ["REJECTED", "APPLIED", "REJECTED"]
    assert results[0]["http_status"] == 404 and results[2]["http_status"] == 422
    assert results[1]["result"]["read_at"] is not None
    [again] = await _push(client, rahul, steal)
    assert again["status"] == "DUPLICATE" and again["original_status"] == "REJECTED"


async def test_one_scheme_conflict_comes_back_explained(client, db, demo, users):
    # Sunita already has a Post-Matric application for 2026-27: an offline duplicate is refused, with the reason.
    item = {"idempotency_key": "dev3-0001-apply", "action": "CREATE_APPLICATION",
            "payload": {"scheme": "POST_MATRIC", "academic_year": "2026-27", "acknowledge_one_scheme_rule": True}}
    [result] = await _push(client, await users.headers("sunita"), item)
    assert result["status"] == "REJECTED" and result["http_status"] == 409
    assert result["error"]["code"] == "ONE_SCHEME_RULE" and result["error"]["can_acknowledge"] is False
    assert await db.scalar(select(func.count()).select_from(Application)
                           .where(Application.student_id == "stu-sunita-001")) == 1


async def test_mitra_outbox_respects_the_session_scope(client, db, demo, users):
    mitra = await users.headers("mitra")
    r = await client.post("/v1/mitra/sessions", headers=mitra,
                          json={"student_id": "stu-sunita-001", "scope": "VIEW_STATUS", "duration_minutes": 30})
    sid = r.json()["session_id"]
    await client.post(f"/v1/mitra/sessions/{sid}/verify", headers=mitra,
                      json={"otp": await latest_sms_code(db, PHONES["sunita"])})
    acting = {**mitra, "X-Mitra-Session": sid}
    deficiency_id = await _deficiency(db, demo["sunita_application"])
    [result] = await _push(client, acting, {
        "idempotency_key": "mitra-0001", "action": "RESPOND_DEFICIENCY",
        "payload": {"application_id": demo["sunita_application"], "deficiency_id": deficiency_id,
                    "response_text": "Helped upload"}})
    assert result["status"] == "REJECTED" and result["http_status"] == 403
    assert (await _pull(client, acting))["events"]  # VIEW_STATUS may read


# ── registration ─────────────────────────────────────────────────────────────

NEW_PHONE = "9000000777"
NEW_STUDENT = {"full_name": "Mina Murmu", "dob": "2009-06-02", "gender": "FEMALE", "state": "Jharkhand",
               "district": "Dumka", "preferred_language": "hi"}


async def test_registration_needs_the_phone_confirmed_by_otp(client, db):
    from app.gateway.models import User
    r = await client.post("/v1/auth/register/start", json={"phone": NEW_PHONE})
    assert r.status_code == 202
    bad = await client.post("/v1/auth/register/complete", json={"phone": NEW_PHONE, "otp": "000000", **NEW_STUDENT})
    code = await latest_sms_code(db, NEW_PHONE)
    assert bad.status_code == 401 or code == "000000"
    assert await db.scalar(select(User.id).where(User.phone == NEW_PHONE)) is None  # nothing created yet

    r = await client.post("/v1/auth/register/complete", json={"phone": NEW_PHONE, "otp": code, **NEW_STUDENT})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "STUDENT" and body["user"]["student_id"].startswith("stu-")
    token = {"Authorization": f"Bearer {body['access_token']}"}

    # Registered, but no application exists: the dashboard must not suggest anything was submitted.
    dash = (await client.get("/v1/me/dashboard", headers=token)).json()
    assert dash["student"]["name"] == "Mina Murmu" and dash["applications"] == []
    # The code is single-use.
    again = await client.post("/v1/auth/register/complete", json={"phone": NEW_PHONE, "otp": code, **NEW_STUDENT})
    assert again.status_code == 409


async def test_registration_does_not_reveal_or_take_over_existing_numbers(client, db, demo):
    r = await client.post("/v1/auth/register/start", json={"phone": PHONES["sunita"]})
    assert r.status_code == 202 and "registered" not in r.json()["message"].lower()
    from app.gateway.models import OutboundSms
    last = (await db.execute(select(OutboundSms).where(OutboundSms.to_phone == PHONES["sunita"])
                             .order_by(OutboundSms.created_at.desc()))).scalars().first()
    assert last.category == "REGISTRATION_EXISTS"  # no code was issued
    r = await client.post("/v1/auth/register/complete", json={"phone": PHONES["sunita"], "otp": "123456", **NEW_STUDENT})
    assert r.status_code == 409
