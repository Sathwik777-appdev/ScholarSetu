"""Logic-audit probes (docs/LOGIC_AUDIT.md). Each test PASSES while the bug it describes is present,
so after a fix the matching probe should FAIL; then delete it and add a normal regression test.

Skipped unless RUN_AUDIT_PROBES=1:   RUN_AUDIT_PROBES=1 pytest tests/audit -v
"""
import asyncio
import os

import pytest
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import jwt
from sqlalchemy import func, select

from app.config import settings
from app.dbt_guardian.models import DbtRetry
from app.ledger.models import Application
from app.ledger.service import LedgerService
from app.shared.types import PaymentState, UserRole
from tests.conftest import PHONES, bearer, latest_sms_code, login, make_user, mocks_data

pytestmark = pytest.mark.skipif(not os.environ.get("RUN_AUDIT_PROBES"), reason="audit probes: RUN_AUDIT_PROBES=1")


# ── demo-mode authentication (uncommitted changes) ───────────────────────────

async def test_bug_demo_token_impersonates_ministry_without_otp(client, demo, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    r = await client.get("/v1/analytics/overview", headers={"Authorization": "Bearer demo-token-9876543240"})
    assert r.status_code == 200 and r.json()["scope"] == "All India"


async def test_bug_garbage_token_reads_sunitas_data(client, demo, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    r = await client.get("/v1/me/dashboard", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 200 and r.json()["student"]["name"] == "Sunita Hansda"


async def test_bug_expired_jwt_accepted(client, db, demo, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    token = await login(client, db, PHONES["district"])
    claims = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    claims["exp"] = int((datetime.now(timezone.utc) - timedelta(days=400)).timestamp())
    expired = jwt.encode(claims, settings.JWT_SECRET, algorithm="HS256")
    assert (await client.get("/v1/analytics/overview", headers=bearer(expired))).status_code == 200


async def test_bug_unknown_phone_with_demo_otp_gets_sunitas_account(client, demo, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    r = await client.post("/v1/auth/otp/verify", json={"phone": "9123456789", "otp": settings.DEMO_OTP})
    assert r.status_code == 200 and r.json()["user"]["name"] == "Sunita Hansda"


async def test_bug_non_demo_user_logs_in_with_demo_otp(client, db, demo, monkeypatch):
    await make_user(db, "9000000999", UserRole.MINISTRY, "Real ministry user", is_demo=False)
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    r = await client.post("/v1/auth/otp/verify", json={"phone": "9000000999", "otp": settings.DEMO_OTP})
    assert r.status_code == 200 and r.json()["user"]["role"] == "MINISTRY"


async def test_bug_registration_without_phone_confirmation(client, demo, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    r = await client.post("/v1/auth/register/complete", json={
        "phone": "9000000555", "otp": settings.DEMO_OTP, "full_name": "Someone Else", "dob": "2009-01-01",
        "gender": "MALE", "state": "Jharkhand", "district": "Dumka"})
    assert r.status_code == 201  # no code was ever sent to this phone


def test_bug_insecure_defaults():
    from app.config import Settings
    fields = Settings.model_fields
    assert fields["DEMO_MODE"].default is True and fields["JWT_EXPIRE_MINUTES"].default == 43200


# ── fabricated data (uncommitted changes) ────────────────────────────────────

async def test_bug_wallet_invents_documents_for_any_student(client, demo, users, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    body = (await client.get("/v1/me/wallet", headers=await users.headers("rahul"))).json()
    titles = [d["title"] for d in body["documents"]]
    assert any("Aadhaar Card (6234 8901 4183)" in t for t in titles)
    assert any(d.get("metadata_json", {}).get("holder") == "Sunita Hansda" for d in body["documents"])  # Rahul sees Sunita


async def test_bug_passport_invents_signed_attestations(client, demo, users, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    body = (await client.get("/v1/me/attestations", headers=await users.headers("rahul"))).json()
    ident = body["attestations"]["IDENTITY"][0]
    assert ident["status"] == "ACTIVE" and ident["claim_value"]["name"] == "Sunita Hansda"
    assert ident["signature"].startswith("mock-jws")
    r = await client.get(f"/v1/attestations/{ident['attestation_id']}/verify", headers=await users.headers("rahul"))
    assert r.status_code == 404  # the "ACTIVE" attestation does not exist


async def test_bug_coverage_invents_numbers_when_linkage_fails(client, demo, users, gov, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    gov.down.add("/udise")  # UDISE+ unreachable: must be 503, not numbers
    r = await client.get("/v1/analytics/coverage", headers=await users.headers("ministry"))
    body = r.json()
    print("coverage with UDISE+ down:", r.status_code, [x["district"] for x in body["rows"]])
    assert r.status_code == 200 and "Shikaripara" in {x["block"] for x in body["rows"]} and body["matched_by_apaar"] == 218


# ── core logic ───────────────────────────────────────────────────────────────

async def _sanction(db, app_id, *amounts):
    ledger = LedgerService(db)
    app = await db.get(Application, app_id)
    payments = await ledger.sanction(app, [(f"Instalment {i}", Decimal(a)) for i, a in enumerate(amounts, 1)], "system:t")
    await db.commit()
    return ledger, app, payments


async def test_bug_concurrent_retries_send_money_twice(client, db, demo, users, gov):
    ledger, app, [p] = await _sanction(db, demo["sunita_application"], "5000")
    await ledger.update_payment(app, p.id, PaymentState.INITIATED, "system:t", pfms_ref="PFMS-X")
    await ledger.update_payment(app, p.id, PaymentState.FAILED, "system:t", failure_code="AADHAAR_NOT_SEEDED")
    app_id, pid = app.id, p.id
    await db.commit()
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    headers = await users.headers("sunita")
    url = f"/v1/dbt/applications/{app_id}/payments/{pid}/retry"
    import importlib
    pfms = importlib.import_module("pfms.router")
    before = sum(1 for x in pfms.PAYMENTS.values() if x["reference"] == pid)
    results = await asyncio.gather(*[client.post(url, headers=headers, json={"confirm_fixed": True}) for _ in range(2)],
                                   return_exceptions=True)
    db.expire_all()
    transfers = sum(1 for x in pfms.PAYMENTS.values() if x["reference"] == pid) - before
    recorded = await db.scalar(select(func.count()).select_from(DbtRetry).where(DbtRetry.status == "SUBMITTED"))
    print("retry statuses", [getattr(r, 'status_code', type(r).__name__) for r in results], "PFMS transfers", transfers, "retries recorded", recorded)
    assert transfers == 2 and recorded < transfers


async def test_bug_failed_instalment_hidden_by_later_credit(client, db, demo, users):
    ledger, app, [p1, p2] = await _sanction(db, demo["sunita_application"], "3000", "2000")
    for p, end in ((p1, PaymentState.FAILED), (p2, PaymentState.CREDITED)):
        await ledger.update_payment(app, p.id, PaymentState.INITIATED, "system:t", pfms_ref=f"R-{p.instalment}")
        await ledger.update_payment(app, p.id, end, "system:t", failure_code="ACCOUNT_CLOSED" if end == PaymentState.FAILED else None)
    await db.commit()
    dash = (await client.get("/v1/me/dashboard", headers=await users.headers("sunita"))).json()
    a = dash["applications"][0]
    money = (await client.get("/v1/me/payments", headers=await users.headers("sunita"))).json()
    assert a["current_state"] == "CREDITED" and "fail" not in (a["next_action"] or "").lower()
    assert money["total_failed"] == 3000


async def test_bug_second_scholarship_can_be_sanctioned(client, db, demo, users):
    from app.eligibility.service import current_academic_year
    await _sanction(db, demo["sunita_application"], "5000")
    r = await client.post("/v1/applications", headers=await users.headers("sunita"),
                          json={"scheme": "NFST", "academic_year": current_academic_year(), "acknowledge_one_scheme_rule": True})
    assert r.status_code == 201
    nfst = r.json()["id"]
    ledger = LedgerService(db)
    app = await db.get(Application, nfst)
    for s in ("INSTITUTE_VERIFICATION", "AUTHORITY_VERIFICATION"):
        from app.shared.types import CanonicalState
        await ledger.transition(app, CanonicalState(s), "system:t")
    await db.commit()
    r = await client.post(f"/v1/officer/applications/{nfst}/sanction", headers=await users.headers("district"),
                          json={"instalments": [{"description": "Fellowship", "amount": 37000}]})
    db.expire_all()
    held = await db.scalar(select(func.count()).select_from(Application).where(
        Application.student_id == "stu-sunita-001", Application.canonical_state == CanonicalState.SANCTIONED))
    assert r.status_code == 200 and held == 2


async def test_bug_sanction_ignores_eligibility_and_open_review(client, db, demo, users, gov):
    from tests.conftest import grant_consent
    sunita = await users.headers("sunita")
    consent = await grant_consent(client, sunita, ["ST_STATUS"])
    await client.post("/v1/verify/claims", headers=sunita, json={
        "application_id": demo["sunita_application"], "required_claims": ["ST_STATUS"], "consent_id": consent})
    r = await client.post(f"/v1/officer/applications/{demo['sunita_application']}/sanction",
                          headers=await users.headers("district"),
                          json={"instalments": [{"description": "Anything", "amount": 9_999_999}]})
    assert r.status_code == 200  # ST status still provisional/in review; amount not checked against the rules


async def test_bug_lowercase_district_is_invisible_to_officers(client, db, demo, users):
    await client.post("/v1/auth/register/start", json={"phone": "9000000444"})
    code = await latest_sms_code(db, "9000000444")
    reg = await client.post("/v1/auth/register/complete", json={
        "phone": "9000000444", "otp": code, "full_name": "Mina Murmu", "dob": "2009-06-02", "gender": "FEMALE",
        "state": "jharkhand", "district": "dumka "})
    token = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    from app.eligibility.service import current_academic_year
    a = await client.post("/v1/applications", headers=token, json={"scheme": "PRE_MATRIC", "academic_year": current_academic_year()})
    assert a.status_code == 201
    ids = {x["id"] for x in (await client.get("/v1/applications", headers=await users.headers("district"))).json()}
    state_ids = {x["id"] for x in (await client.get("/v1/applications", headers=await users.headers("state"))).json()}
    assert a.json()["id"] not in ids and a.json()["id"] not in state_ids


async def test_bug_same_person_registers_twice(client, db, demo):
    for phone in ("9000000661", "9000000662"):
        await client.post("/v1/auth/register/start", json={"phone": phone})
        code = await latest_sms_code(db, phone)
        r = await client.post("/v1/auth/register/complete", json={
            "phone": phone, "otp": code, "full_name": "Sunita Hansda", "dob": "2008-04-12", "gender": "FEMALE",
            "state": "Jharkhand", "district": "Dumka"})
        assert r.status_code == 201  # a third "Sunita Hansda, 2008-04-12, Dumka" student record


async def test_bug_otp_attempt_limit_resets_on_every_new_request(client, db, demo):
    phone = PHONES["sunita"]
    tries = 0
    for _ in range(4):  # 4 rounds x 5 guesses = 20 guesses, never locked out
        await client.post("/v1/auth/otp/request", json={"phone": phone})
        real = await latest_sms_code(db, phone)
        for guess in range(5):
            wrong = f"{(int(real) + guess + 1) % 1_000_000:06d}"
            r = await client.post("/v1/auth/otp/verify", json={"phone": phone, "otp": wrong})
            tries += 1
            assert r.status_code in (401, 429)
    await client.post("/v1/auth/otp/request", json={"phone": phone})
    ok = await client.post("/v1/auth/otp/verify", json={"phone": phone, "otp": await latest_sms_code(db, phone)})
    assert tries == 20 and ok.status_code == 200


async def test_bug_one_malformed_portal_record_stops_the_whole_sync(db, demo, gov):
    from app.adapters.sync_service import AdapterSyncService
    from app.verification.sources import SourceClient
    mocks_data.PORTAL_APPS["nsp"]["NSP-BAD-1"] = {
        "app_id": "NSP-BAD-1", "aadhaar_ref": "AREF-JH-0004912", "scheme": "SOMETHING_NEW", "academic_year": "2026-27",
        "status": "PENDING_INSTITUTE", "status_updated_at": "2026-09-10T10:00:00+05:30",
        "submitted_at": "2026-09-05T10:00:00+05:30", "remarks": "", "payments": []}
    client = SourceClient("http://mocks", transport=gov.transport)
    try:
        raised = None
        try:
            await AdapterSyncService(db, client).sync_all()
        except Exception as exc:  # noqa: BLE001
            raised = type(exc).__name__
    finally:
        await client.aclose()
    assert raised is not None  # not parked: the whole run aborts
    print("sync_all raised", raised)


async def test_bug_gemini_rewrite_is_not_checked_and_key_is_logged(client, demo, users, monkeypatch, caplog):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "SECRET-KEY-123")
    real = httpx.AsyncClient

    def fake(*a, **k):
        def handler(request):
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Aapko ₹99,999 mil chuke hain."}]}}]})
        k["transport"] = httpx.MockTransport(handler)
        return real(*a, **k)
    monkeypatch.setattr(httpx, "AsyncClient", fake)
    caplog.set_level(logging.INFO, logger="httpx")
    ans = (await client.post("/v1/jago/chat", headers=await users.headers("rahul"),
                             json={"message": "Mera paisa kab aayega?", "language": "hi"})).json()
    assert "99,999" in ans["response_text"]
    print("httpx log lines with key:", [r.getMessage()[:120] for r in caplog.records if "SECRET-KEY-123" in r.getMessage()])
