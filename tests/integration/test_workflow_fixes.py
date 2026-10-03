"""Regression tests for docs/WORKFLOW_AUDIT.md: a new DigiLocker student can be verified (W1), sanction and payment
follow the bank check (W2, W4), sessions renew (W3), signed answers say they are test data (W6), an officer's
question can be answered (W8) and old rows are cleaned up (W11)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.dbt_guardian.service import DBTGuardianService
from app.eligibility.service import current_academic_year
from app.gateway.models import RefreshToken, User
from app.ledger.models import Application, Payment
from app.shared.types import PaymentState
from app.verification.sources import SourceClient
from tests.conftest import (
    PHONES, bearer, digilocker_signup, give_bank_account, grant_consent, latest_sms_code, mocks_data,
)

PLAN = [{"description": "Ad-hoc grant", "amount": 1500, "component": "adhoc_grant"}]


async def _sign_in_with_otp(client, db, who="sunita"):
    phone = PHONES[who]
    await client.post("/v1/auth/otp/request", json={"phone": phone})
    r = await client.post("/v1/auth/otp/verify", json={"phone": phone, "otp": await latest_sms_code(db, phone)})
    assert r.status_code == 200, r.text
    return r.json()


# ── W1: a person who signs up with DigiLocker is linked to the government records ────────────────────────────

def _new_person():
    person = {
        "id": "ST9001", "first_name": "Mina", "last_name": "Murmu", "gender": "FEMALE", "dob": "2009-06-02",
        "father_name": "Rakesh Murmu", "mother_name": None, "tribe": "Santal", "state": "Jharkhand",
        "district": "Dumka", "aadhaar": "AREF-JH-0099001", "apaar_id": "APAAR-JH-2026-9001", "phone": "9876543299",
        "sources": {
            "uidai": {"name": "Mina Murmu"},
            "caste": {"certificate_no": "JH/ST/2024/9001", "holder_name": "Mina Murmu", "father_name": "Rakesh Murmu",
                      "district": "Dumka", "category": "ST", "tribe": "Santal", "pvtg": False,
                      "issued_by": "Circle Officer, Dumka", "issue_date": "2024-01-10", "status": "VALID"},
        },
    }
    mocks_data.db["students"].append(person)
    give_bank_account(person["aadhaar"], "Mina Murmu")
    return person


async def test_a_new_digilocker_student_is_verified_without_manual_review(client, db, demo, gov, monkeypatch):
    person = _new_person()
    headers = await digilocker_signup(client, monkeypatch, "TEST-" + person["aadhaar"], "MINA MURMU", "02062009", "F",
                                      eaadhaar=person["aadhaar"], apaar_id=person["apaar_id"])
    r = await client.post("/v1/applications", headers=headers, json={
        "scheme": "PRE_MATRIC", "academic_year": current_academic_year()})
    assert r.status_code == 201, r.text
    claims = ["IDENTITY", "ST_STATUS"]
    consent = await grant_consent(client, headers, claims)
    report = (await client.post("/v1/verify/claims", headers=headers, json={
        "application_id": r.json()["id"], "required_claims": claims, "consent_id": consent})).json()
    by_claim = {c["claim_type"]: c for c in report["claims"]}
    assert by_claim["IDENTITY"]["status"] == "VERIFIED", by_claim["IDENTITY"]
    assert by_claim["ST_STATUS"]["status"] == "VERIFIED", by_claim["ST_STATUS"]
    assert not any("No Aadhaar reference" in str(c) for c in report["claims"])


async def test_the_same_identity_cannot_register_twice(client, db, demo, monkeypatch):
    person = _new_person()
    await digilocker_signup(client, monkeypatch, "TEST-first", "MINA MURMU", "02062009", "F",
                            eaadhaar=person["aadhaar"], apaar_id=person["apaar_id"])
    with pytest.raises(AssertionError) as refused:  # the helper asserts 201
        await digilocker_signup(client, monkeypatch, "TEST-second", "MINA MURMU", "02062009", "F",
                                eaadhaar=person["aadhaar"], apaar_id=person["apaar_id"])
    assert "409" in str(refused.value) or "already exists" in str(refused.value)


# ── W3: a session renews without a new code, and a copied token is caught ─────────────────────────────────

async def test_sign_in_returns_a_refresh_token_that_renews_the_session(client, db, demo):
    first = await _sign_in_with_otp(client, db)
    assert first["refresh_token"] and len(first["refresh_token"]) >= 40
    stored = (await db.execute(select(RefreshToken))).scalars().all()
    assert len(stored) == 1 and first["refresh_token"] not in (stored[0].token_hash, stored[0].id)  # only a hash is kept

    r = await client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 200, r.text
    second = r.json()
    assert second["refresh_token"] != first["refresh_token"] and second["user"]["id"] == first["user"]["id"]
    assert (await client.get("/v1/me/attestations", headers=bearer(second["access_token"]))).status_code == 200


async def test_a_refresh_token_works_once_and_a_replay_ends_the_whole_session(client, db, demo):
    first = await _sign_in_with_otp(client, db)
    second = (await client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})).json()
    replay = await client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401
    # The replay means the old token leaked, so even the newest token of that family is dead.
    assert (await client.post("/v1/auth/refresh", json={"refresh_token": second["refresh_token"]})).status_code == 401


async def test_logout_revokes_the_refresh_token(client, db, demo):
    first = await _sign_in_with_otp(client, db)
    assert (await client.post("/v1/auth/logout", json={"refresh_token": first["refresh_token"]})).status_code == 204
    assert (await client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})).status_code == 401


async def test_refresh_is_refused_for_unknown_expired_and_deactivated(client, db, demo):
    assert (await client.post("/v1/auth/refresh", json={"refresh_token": "x" * 60})).status_code == 401
    first = await _sign_in_with_otp(client, db)
    row = (await db.execute(select(RefreshToken))).scalar_one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db.commit()
    assert (await client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})).status_code == 401

    second = await _sign_in_with_otp(client, db, "rahul")
    user = await db.get(User, second["user"]["id"])
    user.is_active = False
    await db.commit()
    assert (await client.post("/v1/auth/refresh", json={"refresh_token": second["refresh_token"]})).status_code == 401


async def test_an_access_token_is_not_a_refresh_token(client, db, demo):
    first = await _sign_in_with_otp(client, db)
    assert (await client.post("/v1/auth/refresh", json={"refresh_token": first["access_token"]})).status_code == 401


# ── W4: the bank check gates the sanction ─────────────────────────────────────────────────────────────────

async def _sanction(client, headers, app_id):
    return await client.post(f"/v1/officer/applications/{app_id}/sanction", headers=headers, json={
        "instalments": PLAN, "override_reason": "Test: eligibility confirmed offline"})


async def test_sanction_is_refused_while_the_bank_account_would_not_receive_the_money(client, db, demo, users, gov):
    app_id = demo["sunita_application"]
    district = await users.headers("district")
    r = await _sanction(client, district, app_id)  # Sunita's Aadhaar is not seeded for DBT in the test world
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "DBT_HEALTH_CHECK_FAILED" and detail["issues"]
    assert any(i["code"] == "AADHAAR_NOT_SEEDED" for i in detail["issues"])
    db.expire_all()
    assert (await db.get(Application, app_id)).canonical_state.value == "AUTHORITY_VERIFICATION"
    assert (await db.scalar(select(func.count()).select_from(Payment).where(Payment.application_id == app_id))) == 0

    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True  # the bank fixes it
    assert (await _sanction(client, district, app_id)).status_code == 200


async def test_sanction_waits_when_the_bank_check_cannot_run(client, db, demo, users, gov):
    app_id = demo["sunita_application"]
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    gov.down.add("/pfms")
    r = await _sanction(client, await users.headers("district"), app_id)
    assert r.status_code == 503 and r.json()["detail"]["code"] == "DBT_HEALTH_CHECK_UNAVAILABLE"
    db.expire_all()
    assert (await db.get(Application, app_id)).canonical_state.value == "AUTHORITY_VERIFICATION"


# ── W2: sanctioned instalments are paid through PFMS and recorded ─────────────────────────────────────────

async def test_scheduled_instalments_are_sent_to_pfms_and_credited(client, db, demo, users, gov):
    app_id = demo["sunita_application"]
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    assert (await _sanction(client, await users.headers("district"), app_id)).status_code == 200

    sources = SourceClient("http://mocks", transport=gov.transport)
    try:
        service = DBTGuardianService(db, sources)
        await service.process_scheduled_payments()
        await db.commit()
        db.expire_all()
        payment = (await db.execute(select(Payment).where(Payment.application_id == app_id))).scalar_one()
        assert payment.state == PaymentState.INITIATED and payment.pfms_ref
        first_ref = payment.pfms_ref

        await service.process_scheduled_payments()  # nothing is scheduled any more: no second transfer
        await service.poll_in_flight_payments()
        await db.commit()
        db.expire_all()
        payment = (await db.execute(select(Payment).where(Payment.application_id == app_id))).scalar_one()
        assert payment.state == PaymentState.CREDITED and payment.pfms_ref == first_ref
    finally:
        await sources.aclose()
    assert sum(1 for c in gov.calls if c.endswith("/initiate-payment")) == 1
    assert (await db.get(Application, app_id)).canonical_state.value == "CREDITED"


async def test_a_lapsed_account_fails_at_pfms_and_the_student_gets_the_fix_steps(client, db, demo, users, gov):
    app_id = demo["sunita_application"]
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    assert (await _sanction(client, await users.headers("district"), app_id)).status_code == 200
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = False  # the seeding lapsed before the money moved

    sources = SourceClient("http://mocks", transport=gov.transport)
    try:
        service = DBTGuardianService(db, sources)
        await service.process_scheduled_payments()
        await service.poll_in_flight_payments()
    finally:
        await sources.aclose()
    db.expire_all()
    payment = (await db.execute(select(Payment).where(Payment.application_id == app_id))).scalar_one()
    assert payment.state == PaymentState.FAILED and payment.failure_code == "AADHAAR_NOT_SEEDED"
    status = (await client.get(f"/v1/dbt/status/{app_id}", headers=await users.headers("sunita"))).json()
    assert status["payments"][0]["guidance"]["fix_steps"]  # the same plain-language steps as any failed payment


async def test_an_unreachable_bank_service_leaves_the_instalment_scheduled(client, db, demo, users, gov):
    app_id = demo["sunita_application"]
    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = True
    assert (await _sanction(client, await users.headers("district"), app_id)).status_code == 200
    gov.down.add("/pfms")
    sources = SourceClient("http://mocks", transport=gov.transport)
    try:
        await DBTGuardianService(db, sources).process_scheduled_payments()
        await db.commit()
    finally:
        await sources.aclose()
    db.expire_all()
    payment = (await db.execute(select(Payment).where(Payment.application_id == app_id))).scalar_one()
    assert payment.state == PaymentState.SCHEDULED  # tried again on the next pass, not failed


# ── W6: answers from the test services say so ─────────────────────────────────────────────────────────────

async def test_passport_attestations_are_labelled_as_test_data(client, db, demo, users, gov):
    sunita = await users.headers("sunita")
    claims = ["IDENTITY", "INCOME"]
    consent = await grant_consent(client, sunita, claims)
    await client.post("/v1/verify/claims", headers=sunita, json={
        "application_id": demo["sunita_application"], "required_claims": claims, "consent_id": consent})
    passport = (await client.get("/v1/me/attestations", headers=sunita)).json()["attestations"]
    items = [a for group in passport.values() for a in group]
    assert items and all(a["test_data"] is True for a in items)
    assert all(a["source"].endswith("(test)") for a in items if not a["source"].startswith("OFFICER"))
    verdict = (await client.get(f"/v1/attestations/{items[0]['attestation_id']}/verify", headers=sunita)).json()
    assert verdict["is_valid"] and verdict["payload"]["test_data"] is True


# ── W8: the student can answer "more information needed" ──────────────────────────────────────────────────

async def _info_requested_case(client, db, demo, users, gov):
    sunita, district = await users.headers("sunita"), await users.headers("district")
    claims = ["IDENTITY", "ST_STATUS", "INCOME"]
    consent = await grant_consent(client, sunita, claims)
    report = (await client.post("/v1/verify/claims", headers=sunita, json={
        "application_id": demo["sunita_application"], "required_claims": claims, "consent_id": consent})).json()
    case_id = next(c["review_case_id"] for c in report["claims"] if c["claim_type"] == "ST_STATUS")
    r = await client.post(f"/v1/review/cases/{case_id}/decision", headers=district, json={
        "decision": "REQUEST_INFO", "notes": "Upload the original certificate with the seal"})
    assert r.status_code == 200, r.text
    return case_id, sunita, district


async def test_the_student_answers_an_information_request_and_the_officer_sees_it(client, db, demo, users, gov):
    case_id, sunita, district = await _info_requested_case(client, db, demo, users, gov)
    actions = (await client.get("/v1/me/pending-actions", headers=sunita)).json()
    action = next(a for a in actions if a["type"] == "REVIEW_INFO_REQUESTED")
    assert action["action_url"] == f"/v1/review/cases/{case_id}/respond"

    rahul = await users.headers("rahul")
    assert (await client.post(action["action_url"], headers=rahul, json={"response_text": "mine"})).status_code == 404
    r = await client.post(action["action_url"], headers=sunita, json={"response_text": "The seal is on page 2; scan attached"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "PENDING" and r.json()["info_response"].startswith("The seal")

    queue = (await client.get("/v1/review/cases", headers=district, params={"status": "PENDING"})).json()
    assert next(c for c in queue if c["id"] == case_id)["info_response"].startswith("The seal")
    assert not [a for a in (await client.get("/v1/me/pending-actions", headers=sunita)).json()
                if a["type"] == "REVIEW_INFO_REQUESTED"]
    # Answered once; a second answer is refused because nothing is being asked.
    assert (await client.post(action["action_url"], headers=sunita, json={"response_text": "again"})).status_code == 409


# ── W11: old rows are removed, current ones kept ──────────────────────────────────────────────────────────

async def test_retention_removes_only_what_is_no_longer_useful(client, db, demo):
    from app.digilocker.models import DigiLockerLogin, DigiLockerSession
    from app.gateway.models import OtpChallenge
    from app.ledger.models import OutboxMessage
    from app.privacy.retention import purge_expired
    from app.shared.types import OtpPurpose

    now = datetime.now(timezone.utc)
    old, fresh = now - timedelta(days=3), now + timedelta(minutes=5)
    db.add_all([
        OtpChallenge(phone="9000000001", purpose=OtpPurpose.LOGIN, otp_hash="x", expires_at=old),
        OtpChallenge(phone="9000000002", purpose=OtpPurpose.LOGIN, otp_hash="y", expires_at=fresh),
        DigiLockerLogin(state="old-login", code_verifier="v", status="DONE", expires_at=old),
        DigiLockerLogin(state="new-login", code_verifier="v", status="PENDING", expires_at=fresh),
        DigiLockerSession(student_id="stu-sunita-001", user_id=(await db.scalar(select(User.id).limit(1))),
                          state="expired-session", code_verifier="v", status="CONNECTED", access_token="secret-token",
                          expires_at=now - timedelta(minutes=1)),
        DigiLockerSession(student_id="stu-sunita-001", user_id=(await db.scalar(select(User.id).limit(1))),
                          state="live-session", code_verifier="v", status="CONNECTED", access_token="live-token",
                          expires_at=fresh),
        OutboxMessage(message_id="m-old", subject="s", event_type="E", payload={}, published_at=now - timedelta(days=30)),
        OutboxMessage(message_id="m-wait", subject="s", event_type="E", payload={}, published_at=None,
                      created_at=now - timedelta(days=30)),
    ])
    await db.commit()
    counts = await purge_expired(db)
    await db.commit()

    assert counts["login_codes"] == 1 and counts["digilocker_sign_ins"] == 1 and counts["outbox"] == 1
    assert counts["digilocker_tokens_cleared"] == 1
    kept_codes = set((await db.execute(select(OtpChallenge.phone).where(OtpChallenge.phone.in_(["9000000001", "9000000002"])))).scalars())
    assert kept_codes == {"9000000002"}
    sessions = {s.state: s.access_token for s in (await db.execute(select(DigiLockerSession))).scalars()}
    assert sessions["expired-session"] is None and sessions["live-session"] == "live-token"
    assert (await db.scalar(select(func.count()).select_from(OutboxMessage).where(OutboxMessage.message_id == "m-wait"))) == 1
    assert (await db.scalar(select(func.count()).select_from(Application))) >= 1  # records of decisions are never purged


# ── Demo: the student can pretend the bank fixed it, in a demo against the test services only ─────────────────

async def test_the_test_bank_fix_works_only_in_a_demo_and_changes_the_test_bank(client, db, demo, users, gov, monkeypatch):
    sunita = await users.headers("sunita")
    app_id = demo["sunita_application"]
    monkeypatch.setattr("app.dbt_guardian.service.settings.DEMO_MODE", False)
    assert (await client.get(f"/v1/dbt/status/{app_id}", headers=sunita)).json()["can_simulate_bank_fix"] is False
    assert (await client.post(f"/v1/dbt/applications/{app_id}/simulate-bank-fix", headers=sunita)).status_code == 404

    monkeypatch.setattr("app.dbt_guardian.service.settings.DEMO_MODE", True)
    status = (await client.get(f"/v1/dbt/status/{app_id}", headers=sunita)).json()
    assert status["can_simulate_bank_fix"] is True

    assert mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] is False
    r = await client.post(f"/v1/dbt/applications/{app_id}/simulate-bank-fix", headers=sunita)
    assert r.status_code == 204
    assert mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] is True
    check = (await client.post(f"/v1/dbt/health-check/{app_id}", headers=sunita)).json()
    assert check["overall_status"] == "PASS"  # proven through the normal bank check, not assumed

    mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] = False
    monkeypatch.setattr("app.dbt_guardian.service.settings.SOURCES_ARE_TEST", False)  # real sources connected
    assert (await client.get(f"/v1/dbt/status/{app_id}", headers=sunita)).json()["can_simulate_bank_fix"] is False
    assert (await client.post(f"/v1/dbt/applications/{app_id}/simulate-bank-fix", headers=sunita)).status_code == 404
    assert mocks_data.BANK_ACCOUNTS["AREF-JH-0004912"]["seeded"] is False

    monkeypatch.setattr("app.dbt_guardian.service.settings.SOURCES_ARE_TEST", True)
    rahul = await users.headers("rahul")  # someone else's application
    assert (await client.post(f"/v1/dbt/applications/{app_id}/simulate-bank-fix", headers=rahul)).status_code == 404


# ── The test DigiLocker itself returns the identity references ───────────────────────────────────────────────

async def test_the_test_digilocker_returns_the_aadhaar_reference_and_apaar_id(monkeypatch):
    import base64
    import hashlib

    import httpx
    from tests.conftest import mocks_main

    monkeypatch.setenv("DIGILOCKER_CLIENT_ID", "test-client")
    monkeypatch.setenv("DIGILOCKER_CLIENT_SECRET", "test-secret-0123456789")
    mocks_data.generate_synthetic_data()
    rahul = next(p for p in mocks_data.db["students"] if p["phone"] == "9876543211")
    verifier = "v" * 50
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    redirect = "scholarsetu://digilocker-callback"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=mocks_main.app), base_url="http://mocks") as client:
        page = await client.get("/digilocker/public/oauth2/1/authorize", params={
            "response_type": "code", "client_id": "test-client", "redirect_uri": redirect, "state": "s" * 20,
            "code_challenge": challenge, "code_challenge_method": "S256"})
        assert page.status_code == 200 and "9876543211" in page.text  # the sign-in page lists test people
        signed_in = await client.post("/digilocker/public/oauth2/1/authorize", data={
            "response_type": "code", "client_id": "test-client", "redirect_uri": redirect, "state": "s" * 20,
            "code_challenge": challenge, "code_challenge_method": "S256", "mobile": "9876543211", "otp": "123456"})
        assert signed_in.status_code == 302
        code = signed_in.headers["location"].split("code=")[1].split("&")[0]
        token = (await client.post("/digilocker/public/oauth2/1/token", data={
            "grant_type": "authorization_code", "code": code, "client_id": "test-client",
            "client_secret": "test-secret-0123456789", "redirect_uri": redirect, "code_verifier": verifier})).json()
    assert token["eaadhaar"] == rahul["aadhaar"] and token["apaar_id"] == rahul["apaar_id"]
    assert token["digilockerid"] == f"TEST-{rahul['aadhaar']}"
