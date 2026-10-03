"""Stage 2 of production hardening (docs/LOGIC_AUDIT.md L8, L11, L13-L16): money and rule safety."""

import asyncio
import importlib
import logging
from decimal import Decimal

import httpx
from sqlalchemy import select

from app.config import settings
from app.eligibility.service import current_academic_year
from app.ledger.models import Application, LedgerEvent, Payment
from app.ledger.service import LedgerService
from app.shared.types import CanonicalState, PaymentState
from tests.conftest import grant_consent, latest_sms_code, mocks_data


async def _sanction_direct(db, app_id, *amounts):
    ledger = LedgerService(db)
    app = await db.get(Application, app_id)
    payments = await ledger.sanction(app, [(f"Instalment {i}", Decimal(a)) for i, a in enumerate(amounts, 1)], "system:t")
    await db.commit()
    return ledger, app, payments


# ── L8: a retry sends money at most once ─────────────────────────────────────

async def test_concurrent_retries_send_one_transfer(client, db, demo, users, gov):
    ledger, app, [p] = await _sanction_direct(db, demo["sunita_application"], "5000")
    await ledger.update_payment(app, p.id, PaymentState.INITIATED, "system:t", pfms_ref="PFMS-X")
    await ledger.update_payment(app, p.id, PaymentState.FAILED, "system:t", failure_code="AADHAAR_NOT_SEEDED")
    app_id, pid = app.id, p.id
    await db.commit()
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    pfms = importlib.import_module("pfms.router")
    url = f"/v1/dbt/applications/{app_id}/payments/{pid}/retry"
    headers = await users.headers("sunita")
    results = await asyncio.gather(*[client.post(url, headers=headers, json={"confirm_fixed": True}) for _ in range(3)])
    assert sorted(r.status_code for r in results) == [200, 409, 409]
    assert sum(1 for x in pfms.PAYMENTS.values() if str(x["reference"]).startswith(pid)) == 1
    db.expire_all()
    assert (await db.get(Payment, pid)).state == PaymentState.RETRYING


# ── L13: a failed instalment is never hidden ─────────────────────────────────

async def test_failed_instalment_keeps_the_application_failed(client, db, demo, users):
    ledger, app, [p1, p2] = await _sanction_direct(db, demo["sunita_application"], "3000", "2000")
    await ledger.update_payment(app, p1.id, PaymentState.INITIATED, "system:t", pfms_ref="R-1")
    await ledger.update_payment(app, p1.id, PaymentState.FAILED, "system:t", failure_code="ACCOUNT_CLOSED")
    await ledger.update_payment(app, p2.id, PaymentState.INITIATED, "system:t", pfms_ref="R-2")
    await ledger.update_payment(app, p2.id, PaymentState.CREDITED, "system:t")
    await db.commit()
    dash = (await client.get("/v1/me/dashboard", headers=await users.headers("sunita"))).json()
    a = dash["applications"][0]
    assert a["current_state"] == "PAYMENT_FAILED" and "fail" in a["next_action"].lower()
    assert a["money_received"] == 2000


async def test_a_later_failure_after_credit_is_shown(client, db, demo, users):
    ledger, app, [p1, p2] = await _sanction_direct(db, demo["sunita_application"], "3000", "2000")
    for p, end in ((p1, PaymentState.CREDITED), (p2, PaymentState.FAILED)):
        await ledger.update_payment(app, p.id, PaymentState.INITIATED, "system:t", pfms_ref=f"R-{p.instalment}")
        await ledger.update_payment(app, p.id, end, "system:t",
                                    failure_code="ACCOUNT_CLOSED" if end == PaymentState.FAILED else None)
    app_id = app.id
    await db.commit()
    db.expire_all()
    assert (await db.get(Application, app_id)).canonical_state == CanonicalState.PAYMENT_FAILED
    assert (await LedgerService(db).verify_chain(app_id)).valid


# ── L14 and L15: sanction follows the rules ──────────────────────────────────

async def _to_authority(db, app_id):
    ledger = LedgerService(db)
    app = await db.get(Application, app_id)
    for s in (CanonicalState.INSTITUTE_VERIFICATION, CanonicalState.AUTHORITY_VERIFICATION):
        await ledger.transition(app, s, "system:t")
    await db.commit()


async def _sanction(client, headers, app_id, instalments, **extra):
    return await client.post(f"/v1/officer/applications/{app_id}/sanction", headers=headers,
                             json={"instalments": instalments, **extra})


POST_MATRIC_PLAN = [
    {"description": "Maintenance allowance", "amount": 12000, "component": "group_1.hosteller_monthly", "months": 10},
    {"description": "Ad-hoc grant", "amount": 1500, "component": "adhoc_grant"},
]


async def _make_sunita_eligible(client, demo, users):
    sunita = await users.headers("sunita")
    claims = ["IDENTITY", "ST_STATUS", "INCOME", "HIGHER_ED", "ACADEMIC_RECORDS"]
    consent = await grant_consent(client, sunita, claims)
    report = (await client.post("/v1/verify/claims", headers=sunita, json={
        "application_id": demo["sunita_application"], "required_claims": claims, "consent_id": consent})).json()
    case_id = next(c["review_case_id"] for c in report["claims"] if c["claim_type"] == "ST_STATUS")
    return case_id


async def test_sanction_waits_for_open_review_cases_then_follows_the_rules(client, db, demo, users, gov):
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    district = await users.headers("district")
    case_id = await _make_sunita_eligible(client, demo, users)
    r = await _sanction(client, district, demo["sunita_application"], POST_MATRIC_PLAN)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "OPEN_REVIEW_CASES"

    await client.post(f"/v1/review/cases/{case_id}/decision", headers=district,
                      json={"decision": "APPROVE", "notes": "Hansdah is a spelling of Hansda"})
    too_much = [{**POST_MATRIC_PLAN[0], "amount": 50000}, POST_MATRIC_PLAN[1]]
    r = await _sanction(client, district, demo["sunita_application"], too_much)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "OUTSIDE_RULES"
    assert any("above the rules" in v for v in r.json()["detail"]["violations"])

    r = await _sanction(client, district, demo["sunita_application"], POST_MATRIC_PLAN)
    assert r.status_code == 200 and r.json()["canonical_state"] == "SANCTIONED"
    event = (await db.execute(select(LedgerEvent).where(LedgerEvent.application_id == demo["sunita_application"],
                                                        LedgerEvent.type == "Sanctioned"))).scalar_one()
    assert event.payload["eligibility_status"] == "ELIGIBLE" and "override" not in event.payload
    assert [c["component"] for c in event.payload["components"]] == ["group_1.hosteller_monthly", "adhoc_grant"]


async def test_amounts_outside_the_rules_need_a_recorded_override(client, db, demo, users, gov):
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    await LedgerService(db).db.commit()
    r = await _sanction(client, await users.headers("district"), demo["sunita_application"],
                        [{"description": "Special grant", "amount": 99000, "component": "adhoc_grant"}],
                        override_reason="Flood relief order no. 12/2026 of the State Tribal Welfare Department")
    assert r.status_code == 200
    event = (await db.execute(select(LedgerEvent).where(LedgerEvent.application_id == demo["sunita_application"],
                                                        LedgerEvent.type == "Sanctioned"))).scalar_one()
    assert event.payload["override"]["reason"].startswith("Flood relief")
    assert event.payload["override"]["by"].startswith("user:")


async def test_one_scheme_rule_is_enforced_at_sanction(client, db, demo, users, gov):
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    ledger, held, [scheduled] = await _sanction_direct(db, demo["sunita_application"], "5000")
    held_id, scheduled_id = held.id, scheduled.id
    r = await client.post("/v1/applications", headers=await users.headers("sunita"), json={
        "scheme": "NFST", "academic_year": current_academic_year(), "acknowledge_one_scheme_rule": True})
    nfst = r.json()["id"]
    await _to_authority(db, nfst)
    district = await users.headers("district")
    plan = [{"description": "JRF fellowship", "amount": 372000, "component": "jrf_monthly", "months": 12}]
    reason = {"override_reason": "Test: NET-JRF verified offline by the university"}
    r = await _sanction(client, district, nfst, plan, **reason)
    assert r.status_code == 409 and r.json()["detail"]["holding_application_id"] == held_id

    r = await _sanction(client, district, nfst, plan, surrender_application_id=held_id, **reason)
    assert r.status_code == 200
    db.expire_all()
    assert (await db.get(Application, held_id)).canonical_state == CanonicalState.SURRENDERED
    assert (await db.get(Payment, scheduled_id)).state == PaymentState.CANCELLED
    held_states = (await db.execute(select(Application.canonical_state).where(
        Application.student_id == "stu-sunita-001", Application.canonical_state == CanonicalState.SANCTIONED))).scalars().all()
    assert len(held_states) == 1


async def test_surrender_is_refused_while_a_payment_is_on_its_way(client, db, demo, users, gov):
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    ledger, held, [p] = await _sanction_direct(db, demo["sunita_application"], "5000")
    await ledger.update_payment(held, p.id, PaymentState.INITIATED, "system:t", pfms_ref="IN-FLIGHT")
    held_id = held.id
    await db.commit()
    nfst = (await client.post("/v1/applications", headers=await users.headers("sunita"), json={
        "scheme": "NFST", "academic_year": current_academic_year(), "acknowledge_one_scheme_rule": True})).json()["id"]
    await _to_authority(db, nfst)
    r = await _sanction(client, await users.headers("district"), nfst,
                        [{"description": "JRF", "amount": 31000, "component": "jrf_monthly", "months": 1}],
                        surrender_application_id=held_id, override_reason="Test: eligibility confirmed offline")
    assert r.status_code == 409 and "on its way" in r.json()["detail"]


def test_instalment_policy():
    from types import SimpleNamespace as I

    from app.ledger.sanction_policy import check_instalments
    amounts = {"adhoc_grant": {"value": 1500, "unit": "INR per year"},
               "group_1": {"value": {"hosteller_monthly": 1200}, "unit": "INR per month"},
               "tuition_fee": {"value": "actual", "unit": "INR"}}
    ok = [I(component="adhoc_grant", amount=1500, months=None, evidence_note=None),
          I(component="group_1.hosteller_monthly", amount=12000, months=10, evidence_note=None),
          I(component="tuition_fee", amount=45000, months=None, evidence_note="Fee receipt 2026/113")]
    assert check_instalments(amounts, ok) == []
    bad = [I(component="adhoc_grant", amount=1501, months=None, evidence_note=None),
           I(component="group_1.hosteller_monthly", amount=100, months=None, evidence_note=None),
           I(component="group_1", amount=100, months=2, evidence_note=None),
           I(component="tuition_fee", amount=1, months=None, evidence_note=None),
           I(component="imaginary", amount=1, months=None, evidence_note=None)]
    problems = check_instalments(amounts, bad)
    assert len(problems) == 5


# ── L16: OTP limits per phone ────────────────────────────────────────────────

async def test_code_requests_are_limited_per_phone(client, db, demo):
    phone = "9876543211"
    codes = [(await client.post("/v1/auth/otp/request", json={"phone": phone})).status_code for _ in range(6)]
    assert codes == [202] * settings.OTP_REQUESTS_PER_HOUR + [429]


async def test_new_codes_do_not_reset_the_guess_count(client, db, demo):
    phone = "9876543210"
    failures = 0
    for _ in range(3):
        await client.post("/v1/auth/otp/request", json={"phone": phone})
        real = await latest_sms_code(db, phone)
        for guess in range(5):
            if failures >= settings.OTP_FAILURES_PER_HOUR:
                break
            wrong = f"{(int(real) + guess + 1) % 1_000_000:06d}"
            await client.post("/v1/auth/otp/verify", json={"phone": phone, "otp": wrong})
            failures += 1
    await client.post("/v1/auth/otp/request", json={"phone": phone})
    right = await latest_sms_code(db, phone)
    r = await client.post("/v1/auth/otp/verify", json={"phone": phone, "otp": right})
    assert r.status_code == 429  # locked for the hour even with the right code


# ── L11: AI phrasing is opt-in, checked, and keeps the key out of logs ───────

def _fake_gemini(monkeypatch, reply: str, seen: list):
    real = httpx.AsyncClient

    def factory(*a, **k):
        def handler(request):
            seen.append(request)
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": reply}]}}]})
        k["transport"] = httpx.MockTransport(handler)
        return real(*a, **k)
    monkeypatch.setattr(httpx, "AsyncClient", factory)


async def _ask(client, headers, ai_assist):
    return (await client.post("/v1/jago/chat", headers=headers, json={
        "message": "Mera paisa kab aayega?", "language": "hi", "ai_assist": ai_assist})).json()


async def test_ai_phrasing_is_off_unless_asked(client, demo, users, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "SECRET-KEY-123")
    seen: list = []
    _fake_gemini(monkeypatch, "whatever", seen)
    answer = await _ask(client, await users.headers("rahul"), ai_assist=False)
    assert seen == [] and answer["ai_phrased"] is False and answer["response_text"] == answer["verified_text"]


async def test_ai_text_with_a_changed_amount_is_discarded(client, demo, users, monkeypatch, caplog):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "SECRET-KEY-123")
    seen: list = []
    _fake_gemini(monkeypatch, "Aapko ₹99,999 mil chuke hain.", seen)
    caplog.set_level(logging.DEBUG)
    answer = await _ask(client, await users.headers("rahul"), ai_assist=True)
    assert answer["ai_phrased"] is False and "99,999" not in answer["response_text"]
    assert seen and "key=" not in str(seen[0].url) and seen[0].headers["x-goog-api-key"] == "SECRET-KEY-123"
    assert not any("SECRET-KEY-123" in r.getMessage() for r in caplog.records)


async def test_faithful_ai_text_is_used_and_the_verified_answer_kept(client, demo, users, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "SECRET-KEY-123")
    rahul = await users.headers("rahul")
    verified = (await _ask(client, rahul, ai_assist=False))["verified_text"]
    import re
    amount = re.search(r"₹\s?([\d,]+)", verified).group(1)
    # A faithful re-wording keeps every figure and ID of the verified answer, in the same order.
    figures = list(dict.fromkeys(re.findall(r"APP-[A-Z]+-\d{4}-\d{6}|\d[\d,]*(?:\.\d+)?", verified)))
    seen: list = []
    _fake_gemini(monkeypatch, "Rahul, aapki jaankari: " + ", ".join(figures) + ".", seen)
    answer = await _ask(client, rahul, ai_assist=True)
    assert answer["ai_phrased"] is True and amount in answer["response_text"]
    assert answer["verified_text"] == verified


def test_ai_text_that_drops_swaps_or_negates_a_fact_is_refused():
    from app.jago_skill.service import _figures_preserved
    verified = "APP-PM-2026-000002: ₹12,000 credited on 05-07-2026; ₹1,500 failed."
    assert _figures_preserved("APP-PM-2026-000002 ke ₹12,000 05-07-2026 ko aaye; ₹1,500 atke.", verified)
    assert not _figures_preserved("APP-PM-2026-000002: ₹12,000 credited on 05-07-2026.", verified)  # dropped
    assert not _figures_preserved("APP-PM-2026-000002: ₹1,500 credited on 05-07-2026; ₹12,000 failed.",
                                  verified)  # swapped
    assert not _figures_preserved("APP-PM-2026-000002: ₹12,000 not credited on 05-07-2026; ₹1,500 failed.",
                                  verified)  # negated


async def test_mitra_cannot_send_a_students_data_to_the_ai(client, db, demo, users, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "SECRET-KEY-123")
    seen: list = []
    _fake_gemini(monkeypatch, "x", seen)
    mitra = await users.headers("mitra")
    sid = (await client.post("/v1/mitra/sessions", headers=mitra,
                             json={"student_id": "stu-sunita-001", "scope": "VIEW_STATUS", "duration_minutes": 10})).json()["session_id"]
    await client.post(f"/v1/mitra/sessions/{sid}/verify", headers=mitra, json={"otp": await latest_sms_code(db, "9876543210")})
    answer = await _ask(client, {**mitra, "X-Mitra-Session": sid}, ai_assist=True)
    assert seen == [] and answer["ai_phrased"] is False
