"""Security floor: S1 (OTP/roles), S2 (auth everywhere, no cross-student reads), S4 (Mitra), skill auth,
officer jurisdiction."""

import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.config import settings
from app.gateway.models import AssistSession, AuditLog, OtpChallenge, User
from app.main import app
from app.shared.types import UserRole
from tests.conftest import PHONES, bearer, latest_sms_code, login, make_user

# Routes that are intentionally reachable without a user token.
PUBLIC_ROUTES = {
    ("GET", "/health"),
    ("GET", "/health/ready"),
    ("POST", "/v1/auth/otp/request"),
    ("POST", "/v1/auth/otp/verify"),
    ("POST", "/v1/auth/register/start"),     # sends a code; reveals nothing about the number
    ("POST", "/v1/auth/register/complete"),  # needs that code
    ("POST", "/v1/auth/digilocker/callback"),  # returns 501 Not Implemented
    ("GET", "/v1/attestations/public-key"),
    ("POST", "/v1/attestations/verify-jws"),
    ("GET", "/v1/jago/guidelines/search"),      # public scheme text, no personal data
    ("POST", "/v1/skill/tools/{tool_name}"),    # service-token auth, tested separately
    ("POST", "/v1/sms/inbound"),                # SMS gateway webhook: gateway token + registered phone
    ("POST", "/v1/ivr/call"),                   # returns 501 Not Implemented
}


# ── S1: OTP login and roles ──────────────────────────────────────────────────


async def test_universal_otp_with_ministry_role_is_rejected(client, demo):
    r = await client.post("/v1/auth/otp/verify", json={"phone": "9000000001", "otp": "123456", "role": "MINISTRY"})
    assert r.status_code == 401


async def test_role_in_request_body_is_ignored(client, db, demo):
    await client.post("/v1/auth/otp/request", json={"phone": PHONES["sunita"]})
    code = await latest_sms_code(db, PHONES["sunita"])
    r = await client.post("/v1/auth/otp/verify", json={"phone": PHONES["sunita"], "otp": code, "role": "MINISTRY"})
    assert r.status_code == 200 and r.json()["user"]["role"] == "STUDENT"
    assert (await client.get("/v1/analytics/sla", headers=bearer(r.json()["access_token"]))).status_code == 403


async def test_otp_is_never_returned_and_is_stored_hashed(client, db, demo):
    r = await client.post("/v1/auth/otp/request", json={"phone": PHONES["sunita"]})
    code = await latest_sms_code(db, PHONES["sunita"])
    assert "dev_hint" not in r.json() and code not in r.text
    challenge = (await db.execute(select(OtpChallenge))).scalar_one()
    assert challenge.otp_hash != code and len(challenge.otp_hash) == 64


async def test_unregistered_phone_gets_same_answer_and_no_sms(client, db, demo):
    unknown = await client.post("/v1/auth/otp/request", json={"phone": "9000000009"})
    known = await client.post("/v1/auth/otp/request", json={"phone": PHONES["sunita"]})
    assert unknown.status_code == known.status_code == 202
    assert unknown.json()["status"] == known.json()["status"]
    assert (await db.execute(select(OtpChallenge).where(OtpChallenge.phone == "9000000009"))).first() is None


async def test_expired_otp_is_rejected(client, db, demo):
    await client.post("/v1/auth/otp/request", json={"phone": PHONES["sunita"]})
    code = await latest_sms_code(db, PHONES["sunita"])
    challenge = (await db.execute(select(OtpChallenge))).scalar_one()
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()
    assert (await client.post("/v1/auth/otp/verify", json={"phone": PHONES["sunita"], "otp": code})).status_code == 401


async def test_otp_locks_after_five_wrong_attempts(client, db, demo):
    await client.post("/v1/auth/otp/request", json={"phone": PHONES["sunita"]})
    code = await latest_sms_code(db, PHONES["sunita"])
    wrong = "000000" if code != "000000" else "111111"
    statuses = [(await client.post("/v1/auth/otp/verify", json={"phone": PHONES["sunita"], "otp": wrong})).status_code
                for _ in range(5)]
    assert statuses == [401, 401, 401, 401, 429]
    assert (await client.post("/v1/auth/otp/verify", json={"phone": PHONES["sunita"], "otp": code})).status_code == 429


async def test_demo_otp_only_for_demo_users_in_demo_mode(client, db, demo, monkeypatch):
    await make_user(db, "9000000002", UserRole.STUDENT, "Real Student", is_demo=False)
    demo_user = {"phone": PHONES["sunita"], "otp": settings.DEMO_OTP}
    real_user = {"phone": "9000000002", "otp": settings.DEMO_OTP}
    assert (await client.post("/v1/auth/otp/verify", json=demo_user)).status_code == 401  # DEMO_MODE off
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    assert (await client.post("/v1/auth/otp/verify", json=demo_user)).status_code == 200
    assert (await client.post("/v1/auth/otp/verify", json=real_user)).status_code == 401


async def test_token_role_comes_from_database(client, db, users):
    token = await users.token("sunita")
    sunita = (await db.execute(select(User).where(User.phone == PHONES["sunita"]))).scalar_one()
    sunita.role, sunita.jurisdiction_state, sunita.jurisdiction_district = UserRole.DISTRICT_OFFICER, "Jharkhand", "Dumka"
    await db.commit()
    assert (await client.get("/v1/review/cases", headers=bearer(token))).status_code == 200
    sunita.role = UserRole.STUDENT
    await db.commit()
    assert (await client.get("/v1/review/cases", headers=bearer(token))).status_code == 403


# ── S2: authentication on every non-public route ─────────────────────────────


def _all_routes():
    for path, operations in app.openapi()["paths"].items():
        for method in operations:
            yield method.upper(), path


@pytest.mark.parametrize("method,path", sorted(set(_all_routes()) - PUBLIC_ROUTES))
async def test_every_non_public_route_requires_a_token(client, method, path):
    url = re.sub(r"\{[^}]+\}", "x", path)
    r = await client.request(method, url, json={})
    assert r.status_code == 401, f"{method} {path} returned {r.status_code}"


def test_me_routes_are_never_public():
    me_routes = [p for _, p in _all_routes() if p.startswith("/v1/me/")]
    assert len(me_routes) >= 8
    assert not [p for _, p in PUBLIC_ROUTES if p.startswith("/v1/me/")]


async def test_invalid_and_expired_tokens_are_rejected(client, db, demo):
    from app.shared.security import create_access_token
    sunita = (await db.execute(select(User).where(User.phone == PHONES["sunita"]))).scalar_one()
    expired, _ = create_access_token(sunita.id, "STUDENT", expires_delta=timedelta(seconds=-5))
    assert (await client.get("/v1/me/dashboard", headers=bearer(expired))).status_code == 401
    assert (await client.get("/v1/me/dashboard", headers=bearer("not-a-jwt"))).status_code == 401


# ── Student A cannot read student B ──────────────────────────────────────────


async def test_student_sees_only_own_data(client, db, demo, users):
    sunita_app, rahul_app = demo["sunita_application"], demo["rahul_application"]
    rahul = await users.headers("rahul")
    sunita = await users.headers("sunita")

    dash = (await client.get("/v1/me/dashboard", headers=rahul)).json()
    assert dash["student"]["id"] == "stu-rahul-002"
    assert [a["id"] for a in dash["applications"]] == [rahul_app]

    for path in (f"/v1/applications/{sunita_app}", f"/v1/applications/{sunita_app}/timeline",
                 f"/v1/applications/{sunita_app}/verify-chain"):
        assert (await client.get(path, headers=rahul)).status_code == 404, path
    assert (await client.get(f"/v1/applications/{sunita_app}/timeline", headers=sunita)).status_code == 200

    # Query-string student ids are ignored.
    r = await client.get("/v1/me/payments?student_id=stu-sunita-001", headers=rahul)
    assert r.json()["student_id"] == "stu-rahul-002"

    # Sunita's attestation cannot be probed by Rahul.
    from app.attestation.keys import get_signer
    from app.attestation.service import AttestationService
    from app.shared.types import ClaimType, VerificationMethod
    att = await AttestationService(db, get_signer()).issue_attestation(
        "stu-sunita-001", ClaimType.ST_STATUS, {"tribe": "Santal"}, "e-District", VerificationMethod.API, 0.95, None)
    await db.commit()
    assert (await client.get(f"/v1/attestations/{att.id}/verify", headers=rahul)).status_code == 404
    assert (await client.get(f"/v1/attestations/{att.id}/verify", headers=sunita)).json()["is_valid"] is True

    # A student_id in the body is rejected; verifying someone else's application is 404.
    r = await client.post("/v1/applications", headers=rahul,
                          json={"student_id": "stu-sunita-001", "scheme": "NOS", "academic_year": "2026-27"})
    assert r.status_code == 422
    r = await client.post("/v1/verify/claims", headers=rahul,
                          json={"application_id": sunita_app, "required_claims": ["INCOME"], "consent_id": "c1"})
    assert r.status_code == 404


async def test_household_view_is_guardian_only(client, users):
    r = await client.get("/v1/me/household", headers=await users.headers("guardian"))
    assert r.status_code == 200
    assert {s["student"]["id"] for s in r.json()["students"]} == {"stu-sunita-001", "stu-rahul-002"}
    assert (await client.get("/v1/me/household", headers=await users.headers("sunita"))).status_code == 403


# ── officers: roles and jurisdiction ─────────────────────────────────────────


async def test_officer_routes_need_officer_role(client, demo, users):
    student = await users.headers("sunita")
    assert (await client.get("/v1/review/cases", headers=student)).status_code == 403
    assert (await client.get("/v1/review/cases", headers=await users.headers("district"))).status_code == 200
    # A student may check their own bank readiness (demo Scene 4) but never someone else's.
    r = await client.post(f"/v1/dbt/health-check/{demo['sunita_application']}", headers=await users.headers("rahul"))
    assert r.status_code == 404


async def test_officers_only_see_their_jurisdiction(client, db, demo, users):
    await make_user(db, "9000000050", UserRole.DISTRICT_OFFICER, "DWO Ranchi", jurisdiction=("Jharkhand", "Ranchi"))
    ranchi = bearer(await login(client, db, "9000000050"))
    dumka = await users.headers("district")
    app_id = demo["sunita_application"]
    assert (await client.get(f"/v1/applications/{app_id}", headers=dumka)).status_code == 200
    assert (await client.get(f"/v1/applications/{app_id}", headers=ranchi)).status_code == 404
    assert (await client.get("/v1/applications", headers=ranchi)).json() == []
    assert {a["id"] for a in (await client.get("/v1/applications", headers=dumka)).json()} == set(demo.values())
    assert len((await client.get("/v1/applications", headers=await users.headers("ministry"))).json()) == 2


async def test_officer_lifecycle_permissions(client, demo, users):
    app_id = demo["sunita_application"]  # AUTHORITY_VERIFICATION
    institute = await users.headers("institute")
    r = await client.post(f"/v1/officer/applications/{app_id}/sanction", headers=institute,
                          json={"instalments": [{"description": "Maintenance", "amount": 5000}]})
    assert r.status_code == 403
    r = await client.post(f"/v1/officer/applications/{app_id}/transition", headers=institute,
                          json={"to_state": "REJECTED"})
    assert r.status_code == 403
    r = await client.post(f"/v1/officer/applications/{app_id}/deficiencies", headers=await users.headers("district"),
                          json={"code": "INCOME_CERT_EXPIRED", "description": "Upload the FY 2026-27 income certificate"})
    assert r.status_code == 200 and r.json()["canonical_state"] == "DEFICIENCY_RAISED"


# ── S4: Mitra assist sessions ────────────────────────────────────────────────


async def test_mitra_session_limits_are_validated(client, users):
    mitra = await users.headers("mitra")
    for body, status in (({"student_id": "stu-sunita-001", "scope": "VIEW_STATUS", "duration_minutes": 100000}, 422),
                         ({"student_id": "stu-sunita-001", "scope": "FULL_ACCESS", "duration_minutes": 30}, 422),
                         ({"student_id": "stu-nobody", "scope": "VIEW_STATUS", "duration_minutes": 30}, 404)):
        assert (await client.post("/v1/mitra/sessions", headers=mitra, json=body)).status_code == status


async def test_only_mitra_role_can_open_sessions(client, users):
    r = await client.post("/v1/mitra/sessions", headers=await users.headers("sunita"),
                          json={"student_id": "stu-rahul-002", "scope": "VIEW_STATUS", "duration_minutes": 10})
    assert r.status_code == 403


async def test_mitra_session_full_lifecycle(client, db, users):
    mitra = await users.headers("mitra")
    r = await client.post("/v1/mitra/sessions", headers=mitra,
                          json={"student_id": "stu-sunita-001", "scope": "VIEW_STATUS", "duration_minutes": 30})
    assert r.status_code == 201
    session = r.json()
    assert session["status"] == "PENDING_STUDENT_OTP" and session["expires_at"] is None
    sid = session["session_id"]
    acting = {**mitra, "X-Mitra-Session": sid}

    assert (await client.get("/v1/me/dashboard", headers=acting)).status_code == 403  # not yet consented
    code = await latest_sms_code(db, PHONES["sunita"])  # the OTP went to the STUDENT
    wrong = "000000" if code != "000000" else "111111"
    assert (await client.post(f"/v1/mitra/sessions/{sid}/verify", headers=mitra, json={"otp": wrong})).status_code == 401
    r = await client.post(f"/v1/mitra/sessions/{sid}/verify", headers=mitra, json={"otp": code})
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"

    dash = await client.get("/v1/me/dashboard", headers=acting)
    assert dash.status_code == 200 and dash.json()["student"]["id"] == "stu-sunita-001"
    assert (await client.post("/v1/me/wallet/digilocker/pull", headers=acting,
                              json={"doc_type": "MARKSHEET_10", "consent_id": "x"})).status_code == 403
    assert (await client.get("/v1/me/consents", headers=acting)).status_code == 403

    assert (await client.delete(f"/v1/mitra/sessions/{sid}", headers=mitra)).json()["status"] == "ENDED"
    assert (await client.get("/v1/me/dashboard", headers=acting)).status_code == 403

    db.expire_all()
    actions = [a.action for a in (await db.execute(
        select(AuditLog).where(AuditLog.assist_session_id == sid).order_by(AuditLog.occurred_at))).scalars()]
    assert actions == ["MITRA_SESSION_REQUESTED", "MITRA_SESSION_OTP_FAILED", "MITRA_SESSION_STARTED",
                       "MITRA_ACTION", "MITRA_SESSION_ENDED"]


async def test_expired_mitra_session_is_refused(client, db, users):
    mitra = await users.headers("mitra")
    sid = (await client.post("/v1/mitra/sessions", headers=mitra,
                             json={"student_id": "stu-sunita-001", "scope": "VIEW_STATUS", "duration_minutes": 5})).json()["session_id"]
    code = await latest_sms_code(db, PHONES["sunita"])
    await client.post(f"/v1/mitra/sessions/{sid}/verify", headers=mitra, json={"otp": code})
    session = await db.get(AssistSession, sid)
    await db.refresh(session)
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()
    r = await client.get("/v1/me/dashboard", headers={**mitra, "X-Mitra-Session": sid})
    assert r.status_code == 403 and "expired" in r.json()["detail"]


async def test_mitra_cannot_use_another_helpers_session(client, db, users):
    mitra = await users.headers("mitra")
    await make_user(db, "9876543221", UserRole.MITRA, "Other Helper")
    other = bearer(await login(client, db, "9876543221"))
    sid = (await client.post("/v1/mitra/sessions", headers=mitra,
                             json={"student_id": "stu-sunita-001", "scope": "VIEW_STATUS", "duration_minutes": 5})).json()["session_id"]
    code = await latest_sms_code(db, PHONES["sunita"])
    await client.post(f"/v1/mitra/sessions/{sid}/verify", headers=mitra, json={"otp": code})
    assert (await client.get("/v1/me/dashboard", headers={**other, "X-Mitra-Session": sid})).status_code == 403


# ── JAGO skill service auth ──────────────────────────────────────────────────


async def test_skill_tools_need_service_token_and_student_session(client, users):
    student = await users.token("sunita")
    service = {"X-Service-Token": settings.SKILL_SERVICE_TOKEN}
    url = "/v1/skill/tools/get_payments"
    assert (await client.post(url, json={})).status_code == 401
    assert (await client.post(url, json={}, headers={"X-Service-Token": "wrong" * 10})).status_code == 401
    assert (await client.post(url, json={}, headers=service)).status_code == 401  # no student session
    assert (await client.post(url, json={}, headers={**service, "X-Student-Session": student})).status_code == 200
    r = await client.post(url, json={"student_id": "stu-rahul-002"}, headers={**service, "X-Student-Session": student})
    assert r.status_code == 422
    r = await client.post(url, json={"bogus": 1}, headers={**service, "X-Student-Session": student})
    assert r.status_code == 422 and "Traceback" not in r.text and "unexpected keyword" not in r.text


async def test_skill_tools_disabled_without_configured_token(client, monkeypatch):
    monkeypatch.setattr(settings, "SKILL_SERVICE_TOKEN", None)
    r = await client.post("/v1/skill/tools/get_payments", json={}, headers={"X-Service-Token": "x" * 40})
    assert r.status_code == 503


async def test_public_key_endpoint_is_open(client):
    r = await client.get("/v1/attestations/public-key")
    assert r.status_code == 200 and r.json()["keys"][0]["kty"] == "OKP"
