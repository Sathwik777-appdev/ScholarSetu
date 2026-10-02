"""Regression tests for docs/CODEBASE_AUDIT.md (A2, A3, A5, A6, A7, A10, A11).

The race tests interleave two database sessions the way two simultaneous requests would, so they are
deterministic: before the fixes each of them failed."""

import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.config import settings
from app.database import AsyncSessionLocal
from app.gateway.models import OtpChallenge
from app.ledger.models import Application, LedgerEvent
from app.ledger.service import LedgerError, LedgerService
from app.shared.types import CanonicalState, SchemeType, UserRole
from app.wallet.models import WalletDocument
from tests.conftest import PHONES, bearer, login, make_user


# ── A2: OTP guesses are counted even when sent in parallel ────────────────────


async def test_parallel_otp_guesses_cannot_exceed_the_limits(client, db, demo):
    phone = PHONES["rahul"]
    await client.post("/v1/auth/otp/request", json={"phone": phone})
    rs = await asyncio.gather(*[client.post("/v1/auth/otp/verify", json={"phone": phone, "otp": f"{i:06d}"})
                                for i in range(40)])
    checked = sum(1 for r in rs if r.status_code == 401)
    db.expire_all()
    recorded = await db.scalar(select(func.sum(OtpChallenge.attempts)).where(OtpChallenge.phone == phone))
    # At most OTP_MAX_ATTEMPTS guesses are ever checked against the code (the last one is answered 429).
    assert recorded == settings.OTP_MAX_ATTEMPTS and checked == settings.OTP_MAX_ATTEMPTS - 1
    assert {r.status_code for r in rs} <= {401, 429} and any(r.status_code == 429 for r in rs)


# ── A3: the public demo outbox never shows a real person's code ───────────────


async def test_public_sms_outbox_shows_only_demo_accounts(client, db, demo, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    await make_user(db, "9000000077", UserRole.STUDENT, "Real Person", is_demo=False)
    await client.post("/v1/auth/otp/request", json={"phone": "9000000077"})
    await client.post("/v1/auth/otp/request", json={"phone": PHONES["sunita"]})
    page = await client.get("/v1/dev/sms-outbox")
    assert page.status_code == 200 and PHONES["sunita"] in page.text and "9000000077" not in page.text

    assert (await client.get("/v1/dev/sms-outbox/all")).status_code == 401
    student = bearer(await login(client, db, PHONES["rahul"]))
    assert (await client.get("/v1/dev/sms-outbox/all", headers=student)).status_code == 403
    ministry = bearer(await login(client, db, PHONES["ministry"]))
    rows = (await client.get("/v1/dev/sms-outbox/all", headers=ministry)).json()
    assert any(r["to_phone"] == "9000000077" for r in rows)

    monkeypatch.setattr(settings, "DEMO_MODE", False)
    assert (await client.get("/v1/dev/sms-outbox")).status_code == 404
    assert (await client.get("/v1/dev/sms-outbox/all", headers=ministry)).status_code == 404


# ── A5: a state change made meanwhile by someone else is respected ────────────


async def test_an_application_rejected_meanwhile_cannot_be_sanctioned(db, demo):
    app_id = demo["sunita_application"]
    async with AsyncSessionLocal() as a, AsyncSessionLocal() as b:
        app_a, app_b = await a.get(Application, app_id), await b.get(Application, app_id)  # both loaded first
        await LedgerService(a).transition(app_a, CanonicalState.REJECTED, "officer-a")
        await a.commit()
        with pytest.raises(LedgerError) as refused:
            await LedgerService(b).sanction(app_b, [("Maintenance", 12000)], "officer-b")
        await b.rollback()
    assert refused.value.status_code == 409 and "REJECTED" in refused.value.detail
    db.expire_all()
    assert (await db.get(Application, app_id)).canonical_state == CanonicalState.REJECTED
    types = (await db.execute(select(LedgerEvent.type).where(LedgerEvent.application_id == app_id))).scalars().all()
    assert "Sanctioned" not in types


async def test_two_officers_moving_the_same_application_at_once(db, demo):
    app_id = demo["sunita_application"]
    async with AsyncSessionLocal() as a, AsyncSessionLocal() as b:
        app_a, app_b = await a.get(Application, app_id), await b.get(Application, app_id)
        await LedgerService(a).transition(app_a, CanonicalState.REJECTED, "officer-a")
        await a.commit()
        with pytest.raises(LedgerError):
            await LedgerService(b).transition(app_b, CanonicalState.REJECTED, "officer-b")


# ── A6: one open application per scheme and year, enforced by the database ────


async def test_simultaneous_submissions_create_one_application(db, demo):
    student = "stu-rahul-002"
    async with AsyncSessionLocal() as a, AsyncSessionLocal() as b:
        await LedgerService(a).create_application(student, SchemeType.TOP_CLASS, "2026-27", "x")
        await a.commit()
        with pytest.raises(IntegrityError):
            await LedgerService(b).create_application(student, SchemeType.TOP_CLASS, "2026-27", "x")
    n = await db.scalar(select(func.count()).select_from(Application).where(
        Application.student_id == student, Application.scheme == SchemeType.TOP_CLASS))
    assert n == 1


async def test_a_rejected_application_does_not_block_a_new_one(db, demo):
    student = "stu-rahul-002"
    ledger = LedgerService(db)
    first = await ledger.create_application(student, SchemeType.TOP_CLASS, "2026-27", "x")
    for state in (CanonicalState.INSTITUTE_VERIFICATION, CanonicalState.AUTHORITY_VERIFICATION,
                  CanonicalState.REJECTED):
        await ledger.transition(first, state, "x")
    await ledger.create_application(student, SchemeType.TOP_CLASS, "2026-27", "x")
    await db.commit()


async def test_a_constraint_conflict_is_409_not_500():
    from app.main import conflicting_write
    response = await conflicting_write(_FakeRequest(), IntegrityError("INSERT", {}, Exception("duplicate key")))
    assert response.status_code == 409


# ── A7: an unreachable database is 503 WAKING, and a bad query is still 500 ───


class _FakeRequest:
    method, url = "GET", type("U", (), {"path": "/v1/me/dashboard"})()


async def test_unreachable_database_is_503_waking_with_retry_after(monkeypatch):
    from app.main import unhandled_error
    from app.shared import wake
    sent = []
    monkeypatch.setattr(settings, "POWER_MANAGER_URL", "https://power.example")
    monkeypatch.setattr(wake, "_last_sent", 0.0)

    async def fake_send():
        sent.append(True)
    monkeypatch.setattr(wake, "_send", fake_send)

    down = DBAPIError("SELECT 1", {}, ConnectionRefusedError("connection refused"))
    response = await unhandled_error(_FakeRequest(), down)
    await asyncio.sleep(0)
    assert response.status_code == 503 and response.headers["retry-after"] == "60"
    assert b'"code":"WAKING"' in response.body and sent == [True]
    await unhandled_error(_FakeRequest(), down)  # a second failure within a minute sends no second wake
    await asyncio.sleep(0)
    assert sent == [True]

    bad_query = DBAPIError("SELECT nope", {}, ValueError("column nope does not exist"))
    assert (await unhandled_error(_FakeRequest(), bad_query)).status_code == 500


# ── A11: deficiency replies may attach only the student's own documents ───────


async def test_deficiency_reply_attaches_only_the_students_own_documents(client, db, demo, users):
    from app.gateway.models import User
    ids = {}
    for who, student in (("sunita", "stu-sunita-001"), ("rahul", "stu-rahul-002")):
        owner = (await db.execute(select(User).where(User.phone == PHONES[who]))).scalar_one()
        db.add(WalletDocument(id=f"doc-of-{who}", student_id=student, document_type="OTHER", title="A file",
                              source="UPLOAD", storage_key="k", mime_type="application/pdf", size_bytes=1,
                              content_sha256="0" * 64, issuer_signed=False, uploaded_by=owner.id))
        ids[who] = f"doc-of-{who}"
    app = await db.get(Application, demo["sunita_application"])
    deficiency = await LedgerService(db).raise_deficiency(app, "DOC", "Send your marksheet", "DISTRICT_OFFICER", "x")
    url = f"/v1/applications/{app.id}/deficiencies/{deficiency.id}/respond"  # read before commit expires them
    await db.commit()
    sunita = await users.headers("sunita")
    r = await client.post(url, headers=sunita, json={"response_text": "Here", "document_ids": [ids["rahul"]]})
    assert r.status_code == 422 and ids["rahul"] in r.json()["detail"]
    r = await client.post(url, headers=sunita, json={"response_text": "Here", "document_ids": [ids["sunita"]]})
    assert r.status_code == 200 and r.json()["payload"]["document_ids"] == [ids["sunita"]]


# ── A22: a manually approved value has the fields the rules read ──────────────


def test_manual_claim_values_are_checked_per_claim_type():
    from app.shared.types import ClaimType
    from app.verification.claim_values import problems
    assert problems(ClaimType.INCOME, {"annual_income": 120000, "financial_year": "2026-27"}) == []
    assert problems(ClaimType.INCOME, {"income": "low"}) == [
        "'annual_income' is required (number)", "'financial_year' is required (text)"]
    assert problems(ClaimType.INCOME, {"annual_income": "1.2 lakh", "financial_year": "2026-27"}) == [
        "'annual_income' must be a number"]
    assert problems(ClaimType.ST_STATUS, {"tribe": "Santal", "pvtg": False, "verified": True}) == [
        "'verified' is set by ScholarSetu and cannot be entered"]
    assert problems(ClaimType.SCHOOL_ENROLMENT, {"school_name": "GHS Dumka", "class": "13"}) == [
        "'class' must be a class number (1-12)"]
    assert problems(ClaimType.DISABILITY, {"percentage": 140}) == ["'percentage' must be at most 100"]
    assert problems(ClaimType.IDENTITY, {"name": "Sunita Hansda", "dob": "2999-01-01"}) == [
        "'dob' must be a date (YYYY-MM-DD)"]


# ── F1: officer workbench endpoints ───────────────────────────────────────────


async def test_sanction_options_list_the_rule_components(client, demo, users):
    district = await users.headers("district")
    r = await client.get(f"/v1/officer/applications/{demo['sunita_application']}/sanction-options", headers=district)
    assert r.status_code == 200, r.text
    body = r.json()
    components = {c["component"]: c for c in body["components"]}
    assert "group_1.hosteller_monthly" in components and components["group_1.hosteller_monthly"]["kind"] == "monthly"
    assert components["adhoc_grant"]["kind"] == "fixed" and components["adhoc_grant"]["amount"] > 0
    assert body["state"] == "AUTHORITY_VERIFICATION" and body["must_surrender"] == []
    # Institute officers do not sanction; officers elsewhere do not see the application.
    assert (await client.get(f"/v1/officer/applications/{demo['sunita_application']}/sanction-options",
                             headers=await users.headers("institute"))).status_code == 403


async def test_officer_lists_the_students_documents_and_it_is_audited(client, db, demo, users):
    from app.gateway.models import AuditLog, User
    owner = (await db.execute(select(User).where(User.phone == PHONES["sunita"]))).scalar_one()
    db.add(WalletDocument(id="doc-1", student_id="stu-sunita-001", document_type="INCOME_CERTIFICATE",
                          title="Income certificate", source="UPLOAD", storage_key="k", mime_type="application/pdf",
                          size_bytes=1, content_sha256="0" * 64, issuer_signed=False, uploaded_by=owner.id))
    await db.commit()
    r = await client.get(f"/v1/officer/applications/{demo['sunita_application']}/documents",
                         headers=await users.headers("district"))
    assert r.status_code == 200 and [d["id"] for d in r.json()] == ["doc-1"]
    assert r.json()[0]["source_label"] == "Uploaded by you"
    assert await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "OFFICER_LISTED_WALLET")) == 1
    assert (await client.get(f"/v1/officer/applications/{demo['sunita_application']}/documents",
                             headers=await users.headers("sunita"))).status_code == 403


async def test_rejecting_needs_a_reason(client, demo, users):
    district = await users.headers("district")
    url = f"/v1/officer/applications/{demo['sunita_application']}/transition"
    r = await client.post(url, headers=district, json={"to_state": "REJECTED"})
    assert r.status_code == 422 and "rejected" in r.json()["detail"]
    r = await client.post(url, headers=district, json={"to_state": "REJECTED", "note": "Income above the ceiling"})
    assert r.status_code == 200 and r.json()["canonical_state"] == "REJECTED"


# ── F2: the verification plan a student consents to ───────────────────────────


async def test_verification_plan_lists_the_rules_claims_and_their_sources(client, demo, users, gov):
    sunita = await users.headers("sunita")
    app_id = demo["sunita_application"]
    r = await client.get(f"/v1/applications/{app_id}/verification-plan", headers=sunita)
    assert r.status_code == 200, r.text
    plan = r.json()
    claims = {c["claim_type"]: c for c in plan["claims"]}
    assert plan["claims"][0]["claim_type"] == "IDENTITY"
    assert {"ST_STATUS", "INCOME"} <= set(claims)  # Post-Matric rules read both
    assert "e-District" in claims["INCOME"]["sources"] and claims["INCOME"]["status"] == "NOT_VERIFIED"
    assert plan["consent"]["data_items"] == [c["claim_type"] for c in plan["claims"]]

    # Consent to exactly that list, verify, and the plan reflects the outcome.
    consent = (await client.post("/v1/consents", headers=sunita, json={
        k: plan["consent"][k] for k in ("requester", "purpose", "data_items", "duration_days")})).json()["id"]
    report = await client.post("/v1/verify/claims", headers=sunita, json={
        "application_id": app_id, "required_claims": plan["consent"]["data_items"], "consent_id": consent})
    assert report.status_code == 200, report.text
    after = {c["claim_type"]: c for c in (await client.get(f"/v1/applications/{app_id}/verification-plan",
                                                           headers=sunita)).json()["claims"]}
    assert after["INCOME"]["status"] == "VERIFIED" and after["INCOME"]["verified_by"] == "e-District"
    # F9: each signed attestation fits in one QR code (binary mode, error correction L: 2953 bytes).
    passport = (await client.get("/v1/me/attestations", headers=sunita)).json()["attestations"]
    signatures = [a["signature"] for items in passport.values() for a in items]
    assert signatures and max(len(s) for s in signatures) <= 2900
    assert (await client.get(f"/v1/applications/{app_id}/verification-plan",
                             headers=await users.headers("rahul"))).status_code == 404


# ── F3: data rights (export, erasure and correction requests) ─────────────────


async def test_student_exports_their_data_without_secrets(client, db, demo, users):
    from app.gateway.models import AuditLog
    sunita = await users.headers("sunita")
    r = await client.get("/v1/me/data-export", headers=sunita)
    assert r.status_code == 200, r.text
    export = r.json()
    assert export["student"]["id"] == "stu-sunita-001" and export["applications"]
    assert all(e["student_id"] == "stu-sunita-001" for e in export["ledger_events"])
    assert "otp_hash" not in r.text and "access_token" not in r.text
    assert await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "DATA_EXPORTED")) == 1
    assert (await client.get("/v1/me/data-export", headers=await users.headers("district"))).status_code == 403


async def test_erasure_request_is_decided_by_an_officer_in_the_jurisdiction(client, db, demo, users):
    sunita = await users.headers("sunita")
    r = await client.post("/v1/me/data-requests", headers=sunita,
                          json={"kind": "ERASURE", "details": "Please delete my old phone number and documents"})
    assert r.status_code == 201 and r.json()["status"] == "OPEN"
    request_id = r.json()["id"]

    district = await users.headers("district")
    listed = (await client.get("/v1/data-requests", headers=district)).json()
    assert [x["id"] for x in listed] == [request_id] and listed[0]["student_name"] == "Sunita Hansda"
    r = await client.post(f"/v1/data-requests/{request_id}/resolve", headers=district,
                          json={"status": "DONE", "resolution": "Old documents deleted; ledger kept by law"})
    assert r.status_code == 200 and r.json()["status"] == "DONE"
    again = await client.post(f"/v1/data-requests/{request_id}/resolve", headers=district,
                              json={"status": "DECLINED", "resolution": "Changing my mind here"})
    assert again.status_code == 409
    mine = (await client.get("/v1/me/data-requests", headers=sunita)).json()
    assert mine[0]["resolution"] == "Old documents deleted; ledger kept by law"


# ── F6: per-client limits on the login endpoints ──────────────────────────────


async def test_one_client_cannot_spray_code_requests_across_many_numbers(client, demo, monkeypatch):
    from app.shared import ratelimit
    monkeypatch.setattr(settings, "IP_CODE_REQUESTS_PER_10_MIN", 3)
    ratelimit.reset()
    try:
        attacker = {"X-Forwarded-For": "6.6.6.6, 203.0.113.9"}  # the first hop is client-supplied and ignored
        codes = [(await client.post("/v1/auth/otp/request", headers=attacker,
                                    json={"phone": f"90000000{i:02d}"})).status_code for i in range(5)]
        assert codes == [202, 202, 202, 429, 429]
        forged = {"X-Forwarded-For": "1.2.3.4, 203.0.113.9"}  # a new forged first hop does not reset the count
        assert (await client.post("/v1/auth/otp/request", headers=forged, json={"phone": "9000000099"})).status_code == 429
        other = {"X-Forwarded-For": "198.51.100.7"}
        assert (await client.post("/v1/auth/otp/request", headers=other, json={"phone": "9000000098"})).status_code == 202
    finally:
        ratelimit.reset()


async def test_a_stopped_cloud_sql_socket_is_503_waking(monkeypatch):
    """A stopped Cloud SQL instance has no unix socket: asyncpg's connect raises a bare FileNotFoundError."""
    import asyncio as aio
    from app.main import unhandled_error
    from app.shared import wake
    monkeypatch.setattr(settings, "POWER_MANAGER_URL", "https://power.example")
    monkeypatch.setattr(wake, "_last_sent", 0.0)

    async def fake_send():
        return None
    monkeypatch.setattr(wake, "_send", fake_send)

    async def create_unix_connection():  # same function name as uvloop/asyncio's socket connect
        raise FileNotFoundError(2, "No such file or directory")
    try:
        await create_unix_connection()
    except FileNotFoundError as exc:
        response = await unhandled_error(_FakeRequest(), exc)
    await aio.sleep(0)
    assert response.status_code == 503 and b"WAKING" in response.body
    other = FileNotFoundError(2, "No such file or directory", "/rules/missing.json")
    assert (await unhandled_error(_FakeRequest(), other)).status_code == 500  # a real missing file stays a bug


async def test_applications_search_and_open_only(client, demo, users):
    ministry = await users.headers("ministry")
    found = (await client.get("/v1/applications", headers=ministry, params={"q": "sunita"})).json()
    assert [a["student_name"] for a in found] == ["Sunita Hansda"]
    by_id = (await client.get("/v1/applications", headers=ministry, params={"q": demo["sunita_application"][-6:]})).json()
    assert [a["id"] for a in by_id] == [demo["sunita_application"]]
    open_ids = {a["id"] for a in (await client.get("/v1/applications", headers=ministry,
                                                   params={"open_only": "true"})).json()}
    assert demo["rahul_application"] not in open_ids and demo["sunita_application"] in open_ids  # Rahul's is credited


def test_jago_understands_the_apps_suggested_questions_and_romanised_hindi():
    from app.jago_skill.tools import Intent, detect_intent
    # The three suggestion chips in the app (lib/ui/jago_screen.dart), both languages.
    assert detect_intent("मेरी छात्रवृत्ति की स्थिति क्या है?") == Intent.STATUS_CHECK
    assert detect_intent("मेरा पैसा कब आएगा?") == Intent.PAYMENT_INFO
    assert detect_intent("क्या कोई काम बाकी है?") == Intent.DEFICIENCY_HELP
    assert detect_intent("What is my scholarship status?") == Intent.STATUS_CHECK
    assert detect_intent("When will my money come?") == Intent.PAYMENT_INFO
    assert detect_intent("Is anything pending from me?") == Intent.DEFICIENCY_HELP
    assert detect_intent("Meri scholarship ki sthiti kya hai?") == Intent.STATUS_CHECK
    assert detect_intent("mera kya kaam baaki hai") == Intent.DEFICIENCY_HELP
