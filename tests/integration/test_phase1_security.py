"""Phase 1 security floor: S1 (OTP/roles), S2 (auth everywhere), S4 (Mitra), skill-service auth."""

import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.config import settings
from app.gateway.models import AssistSession, AuditLog, OtpChallenge
from app.main import app
from app.shared.types import UserRole
from tests.conftest import RAHUL_STUDENT, SUNITA_STUDENT, bearer, latest_sms_code, login, make_student, make_user

SUNITA = ("9876543210", "stu-sunita-001")
RAHUL = ("9876543211", "stu-rahul-002")

# Routes that are intentionally reachable without a user token.
PUBLIC_ROUTES = {
    ("GET", "/health"),
    ("POST", "/v1/auth/otp/request"),
    ("POST", "/v1/auth/otp/verify"),
    ("POST", "/v1/auth/digilocker/callback"),  # returns 501 Not Implemented
    ("GET", "/v1/attestations/public-key"),
    ("POST", "/v1/attestations/verify-jws"),
    ("GET", "/v1/jago/guidelines/search"),      # public scheme text, no personal data
    ("POST", "/v1/skill/tools/{tool_name}"),    # service-token auth, tested separately
}


async def _students(db):
    await make_student(db, **SUNITA_STUDENT)
    await make_student(db, **RAHUL_STUDENT)
    await make_user(db, SUNITA[0], UserRole.STUDENT, "Sunita Hansda", student_id=SUNITA[1],
                    household_id="hh_hansda_001", is_demo=True)
    await make_user(db, RAHUL[0], UserRole.STUDENT, "Rahul Hansda", student_id=RAHUL[1],
                    household_id="hh_hansda_001", is_demo=True)


# ── S1: OTP login and roles ──────────────────────────────────────────────────


async def test_universal_otp_with_ministry_role_is_rejected(client, db):
    r = await client.post("/v1/auth/otp/verify",
                          json={"phone": "9000000001", "otp": "123456", "role": "MINISTRY"})
    assert r.status_code == 401


async def test_role_in_request_body_is_ignored(client, db):
    await _students(db)
    await client.post("/v1/auth/otp/request", json={"phone": SUNITA[0]})
    code = await latest_sms_code(db, SUNITA[0])
    r = await client.post("/v1/auth/otp/verify", json={"phone": SUNITA[0], "otp": code, "role": "MINISTRY"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "STUDENT"
    token = r.json()["access_token"]
    assert (await client.get("/v1/analytics/coverage", headers=bearer(token))).status_code == 403


async def test_otp_is_never_returned_and_is_stored_hashed(client, db):
    await _students(db)
    r = await client.post("/v1/auth/otp/request", json={"phone": SUNITA[0]})
    code = await latest_sms_code(db, SUNITA[0])
    assert "dev_hint" not in r.json() and code not in r.text
    challenge = (await db.execute(select(OtpChallenge))).scalar_one()
    assert challenge.otp_hash != code and len(challenge.otp_hash) == 64


async def test_unregistered_phone_gets_same_answer_and_no_sms(client, db):
    await _students(db)
    unknown = await client.post("/v1/auth/otp/request", json={"phone": "9000000009"})
    known = await client.post("/v1/auth/otp/request", json={"phone": SUNITA[0]})
    assert unknown.status_code == known.status_code == 202
    assert unknown.json()["status"] == known.json()["status"]
    assert (await db.execute(select(OtpChallenge).where(OtpChallenge.phone == "9000000009"))).first() is None


async def test_expired_otp_is_rejected(client, db):
    await _students(db)
    await client.post("/v1/auth/otp/request", json={"phone": SUNITA[0]})
    code = await latest_sms_code(db, SUNITA[0])
    challenge = (await db.execute(select(OtpChallenge))).scalar_one()
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()
    r = await client.post("/v1/auth/otp/verify", json={"phone": SUNITA[0], "otp": code})
    assert r.status_code == 401


async def test_otp_locks_after_five_wrong_attempts(client, db):
    await _students(db)
    await client.post("/v1/auth/otp/request", json={"phone": SUNITA[0]})
    code = await latest_sms_code(db, SUNITA[0])
    wrong = "000000" if code != "000000" else "111111"
    statuses = [(await client.post("/v1/auth/otp/verify", json={"phone": SUNITA[0], "otp": wrong})).status_code
                for _ in range(5)]
    assert statuses == [401, 401, 401, 401, 429]
    r = await client.post("/v1/auth/otp/verify", json={"phone": SUNITA[0], "otp": code})
    assert r.status_code == 429


async def test_demo_otp_only_for_demo_users_in_demo_mode(client, db, monkeypatch):
    await _students(db)
    await make_user(db, "9000000002", UserRole.STUDENT, "Real Student", student_id="stu-real-1", is_demo=False)
    demo = {"phone": SUNITA[0], "otp": settings.DEMO_OTP}
    real = {"phone": "9000000002", "otp": settings.DEMO_OTP}

    assert (await client.post("/v1/auth/otp/verify", json=demo)).status_code == 401  # DEMO_MODE off

    monkeypatch.setattr(settings, "DEMO_MODE", True)
    assert (await client.post("/v1/auth/otp/verify", json=demo)).status_code == 200
    assert (await client.post("/v1/auth/otp/verify", json=real)).status_code == 401


async def test_token_role_comes_from_database(client, db):
    await _students(db)
    token = await login(client, db, SUNITA[0])
    user = (await db.execute(select(AuditLog))).scalars().first()
    assert user is not None  # login was audited
    # Promote in the DB: the same token now carries officer rights; demote: they vanish.
    from app.gateway.models import User
    sunita = (await db.execute(select(User).where(User.phone == SUNITA[0]))).scalar_one()
    sunita.role = UserRole.DISTRICT_OFFICER
    await db.commit()
    assert (await client.get("/v1/review/cases", headers=bearer(token))).status_code == 200
    sunita.role = UserRole.STUDENT
    await db.commit()
    assert (await client.get("/v1/review/cases", headers=bearer(token))).status_code == 403


# ── S2: authentication on every non-public route ─────────────────────────────


def _all_routes():
    # The OpenAPI schema lists every mounted route regardless of how routers are nested.
    for path, operations in app.openapi()["paths"].items():
        for method in operations:
            yield method.upper(), path


@pytest.mark.parametrize("method,path", sorted(set(_all_routes()) - PUBLIC_ROUTES))
async def test_every_non_public_route_requires_a_token(client, method, path):
    url = re.sub(r"\{[^}]+\}", "x", path)
    r = await client.request(method, url, json={})
    assert r.status_code == 401, f"{method} {path} returned {r.status_code}"


def test_all_me_routes_are_covered():
    me_routes = [p for _, p in _all_routes() if p.startswith("/v1/me/")]
    assert len(me_routes) >= 8
    assert not [(m, p) for m, p in PUBLIC_ROUTES if p.startswith("/v1/me/")]


async def test_invalid_and_expired_tokens_are_rejected(client, db):
    await _students(db)
    from app.shared.security import create_access_token
    from app.gateway.models import User
    sunita = (await db.execute(select(User).where(User.phone == SUNITA[0]))).scalar_one()
    expired, _ = create_access_token(sunita.id, "STUDENT", expires_delta=timedelta(seconds=-5))
    assert (await client.get("/v1/me/dashboard", headers=bearer(expired))).status_code == 401
    assert (await client.get("/v1/me/dashboard", headers=bearer("not-a-jwt"))).status_code == 401


# ── Student A cannot read student B ──────────────────────────────────────────


async def test_student_sees_only_own_data(client, db):
    await _students(db)
    sunita = await login(client, db, SUNITA[0])
    rahul = await login(client, db, RAHUL[0])

    dash = (await client.get("/v1/me/dashboard", headers=bearer(rahul))).json()
    assert dash["student"]["id"] == RAHUL[1]
    assert {a["id"] for a in dash["applications"]} == {"APP-PRM-2025-004192"}

    # Rahul cannot open Sunita's timeline or payments
    r = await client.get("/v1/applications/APP-PM-2026-000812/timeline", headers=bearer(rahul))
    assert r.status_code == 404
    assert (await client.get("/v1/me/payments", headers=bearer(rahul))).status_code == 404
    # ...while Sunita can
    r = await client.get("/v1/applications/APP-PM-2026-000812/timeline", headers=bearer(sunita))
    assert r.status_code == 200 and len(r.json()) >= 1
    assert (await client.get("/v1/me/payments", headers=bearer(sunita))).json()["sanctioned"] == 14500.0

    # Query-string student_id is ignored
    r = await client.get("/v1/me/attestations?student_id=stu-sunita-001", headers=bearer(rahul))
    assert r.json()["student_id"] == RAHUL[1]
    assert all(not v for v in r.json()["attestations"].values())

    # Sunita's attestation cannot be probed by Rahul
    from app.attestation.keys import get_signer
    from app.attestation.service import AttestationService
    from app.shared.types import ClaimType, VerificationMethod
    att = await AttestationService(db, get_signer()).issue_attestation(
        SUNITA[1], ClaimType.ST_STATUS, {"tribe": "Santal"}, "e-District", VerificationMethod.API, 0.95, None)
    await db.commit()
    passport = (await client.get("/v1/me/attestations", headers=bearer(sunita))).json()
    att_id = passport["attestations"]["ST_STATUS"][0]["attestation_id"]
    assert att_id == att.id
    assert (await client.get(f"/v1/attestations/{att_id}/verify", headers=bearer(rahul))).status_code == 404
    ok = await client.get(f"/v1/attestations/{att_id}/verify", headers=bearer(sunita))
    assert ok.json() == {"is_valid": True, "reason": None}

    # Body student_id is rejected when creating an application
    r = await client.post("/v1/applications", headers=bearer(rahul),
                          json={"student_id": SUNITA[1], "scheme": "NOS", "academic_year": "2026-27"})
    assert r.status_code == 422

    # A student cannot run verification on someone else's application
    r = await client.post("/v1/verify/claims", headers=bearer(rahul),
                          json={"application_id": "APP-PM-2026-000812", "required_claims": ["INCOME"],
                                "consent_id": "c1"})
    assert r.status_code == 404


async def test_household_view_is_guardian_only(client, db):
    await _students(db)
    await make_user(db, "9876543212", UserRole.GUARDIAN, "Babulal Hansda", household_id="hh_hansda_001")
    guardian = await login(client, db, "9876543212")
    sunita = await login(client, db, SUNITA[0])
    r = await client.get("/v1/me/household", headers=bearer(guardian))
    assert r.status_code == 200
    assert {s["student"]["id"] for s in r.json()["students"]} == {SUNITA[1], RAHUL[1]}
    assert (await client.get("/v1/me/household", headers=bearer(sunita))).status_code == 403


async def test_officer_routes_need_officer_role(client, db):
    await _students(db)
    await make_user(db, "9876543230", UserRole.DISTRICT_OFFICER, "DWO Dumka")
    student = await login(client, db, SUNITA[0])
    officer = await login(client, db, "9876543230")
    assert (await client.get("/v1/review/cases", headers=bearer(student))).status_code == 403
    assert (await client.get("/v1/review/cases", headers=bearer(officer))).status_code == 200
    assert (await client.post("/v1/dbt/health-check/APP-PM-2026-000812", headers=bearer(student))).status_code == 403


# ── S4: Mitra assist sessions ────────────────────────────────────────────────


async def _mitra_setup(client, db):
    await _students(db)
    await make_user(db, "9876543220", UserRole.MITRA, "Kavita Tudu (Hostel Warden)")
    return await login(client, db, "9876543220")


async def test_mitra_session_limits_are_validated(client, db):
    mitra = await _mitra_setup(client, db)
    too_long = await client.post("/v1/mitra/sessions", headers=bearer(mitra),
                                 json={"student_id": SUNITA[1], "scope": "VIEW_STATUS", "duration_minutes": 100000})
    assert too_long.status_code == 422
    full = await client.post("/v1/mitra/sessions", headers=bearer(mitra),
                             json={"student_id": SUNITA[1], "scope": "FULL_ACCESS", "duration_minutes": 30})
    assert full.status_code == 422
    unknown = await client.post("/v1/mitra/sessions", headers=bearer(mitra),
                                json={"student_id": "stu-nobody", "scope": "VIEW_STATUS", "duration_minutes": 30})
    assert unknown.status_code == 404


async def test_only_mitra_role_can_open_sessions(client, db):
    await _students(db)
    student = await login(client, db, SUNITA[0])
    r = await client.post("/v1/mitra/sessions", headers=bearer(student),
                          json={"student_id": RAHUL[1], "scope": "VIEW_STATUS", "duration_minutes": 10})
    assert r.status_code == 403


async def test_mitra_session_full_lifecycle(client, db):
    mitra = await _mitra_setup(client, db)
    r = await client.post("/v1/mitra/sessions", headers=bearer(mitra),
                          json={"student_id": SUNITA[1], "scope": "VIEW_STATUS", "duration_minutes": 30})
    assert r.status_code == 201
    session = r.json()
    assert session["status"] == "PENDING_STUDENT_OTP" and session["expires_at"] is None
    sid = session["session_id"]
    acting = {**bearer(mitra), "X-Mitra-Session": sid}

    # Not usable until the student's OTP is verified
    assert (await client.get("/v1/me/dashboard", headers=acting)).status_code == 403
    # The OTP went to the STUDENT's phone, not the helper's
    code = await latest_sms_code(db, SUNITA[0])
    wrong = "000000" if code != "000000" else "111111"
    assert (await client.post(f"/v1/mitra/sessions/{sid}/verify", headers=bearer(mitra),
                              json={"otp": wrong})).status_code == 401
    r = await client.post(f"/v1/mitra/sessions/{sid}/verify", headers=bearer(mitra), json={"otp": code})
    assert r.status_code == 200 and r.json()["status"] == "ACTIVE"

    # In scope: view status of Sunita
    dash = await client.get("/v1/me/dashboard", headers=acting)
    assert dash.status_code == 200 and dash.json()["student"]["id"] == SUNITA[1]
    # Out of scope: uploading or responding
    r = await client.post("/v1/me/wallet/digilocker/pull", headers=acting, json={"doc_type": "MARKSHEET_10"})
    assert r.status_code == 403
    # Never allowed for a Mitra: consents and new applications
    assert (await client.get("/v1/me/consents", headers=acting)).status_code == 403

    # End it; further use fails
    assert (await client.delete(f"/v1/mitra/sessions/{sid}", headers=bearer(mitra))).json()["status"] == "ENDED"
    assert (await client.get("/v1/me/dashboard", headers=acting)).status_code == 403

    db.expire_all()
    actions = [a.action for a in (await db.execute(
        select(AuditLog).where(AuditLog.assist_session_id == sid).order_by(AuditLog.occurred_at))).scalars()]
    assert actions == ["MITRA_SESSION_REQUESTED", "MITRA_SESSION_OTP_FAILED", "MITRA_SESSION_STARTED",
                       "MITRA_ACTION", "MITRA_SESSION_ENDED"]


async def test_expired_mitra_session_is_refused(client, db):
    mitra = await _mitra_setup(client, db)
    sid = (await client.post("/v1/mitra/sessions", headers=bearer(mitra),
                             json={"student_id": SUNITA[1], "scope": "VIEW_STATUS", "duration_minutes": 5})).json()["session_id"]
    code = await latest_sms_code(db, SUNITA[0])
    await client.post(f"/v1/mitra/sessions/{sid}/verify", headers=bearer(mitra), json={"otp": code})
    session = await db.get(AssistSession, sid)
    await db.refresh(session)
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()
    r = await client.get("/v1/me/dashboard", headers={**bearer(mitra), "X-Mitra-Session": sid})
    assert r.status_code == 403 and "expired" in r.json()["detail"]


async def test_mitra_cannot_use_another_helpers_session(client, db):
    mitra = await _mitra_setup(client, db)
    await make_user(db, "9876543221", UserRole.MITRA, "Other Helper")
    other = await login(client, db, "9876543221")
    sid = (await client.post("/v1/mitra/sessions", headers=bearer(mitra),
                             json={"student_id": SUNITA[1], "scope": "VIEW_STATUS", "duration_minutes": 5})).json()["session_id"]
    code = await latest_sms_code(db, SUNITA[0])
    await client.post(f"/v1/mitra/sessions/{sid}/verify", headers=bearer(mitra), json={"otp": code})
    r = await client.get("/v1/me/dashboard", headers={**bearer(other), "X-Mitra-Session": sid})
    assert r.status_code == 403


# ── JAGO skill service auth ──────────────────────────────────────────────────


async def test_skill_tools_need_service_token_and_student_session(client, db):
    await _students(db)
    student = await login(client, db, SUNITA[0])
    service = {"X-Service-Token": settings.SKILL_SERVICE_TOKEN}
    url = "/v1/skill/tools/get_payments"

    assert (await client.post(url, json={})).status_code == 401
    assert (await client.post(url, json={}, headers={"X-Service-Token": "wrong" * 10})).status_code == 401
    assert (await client.post(url, json={}, headers=service)).status_code == 401  # no student session
    r = await client.post(url, json={}, headers={**service, "X-Student-Session": student})
    assert r.status_code == 200
    r = await client.post(url, json={"student_id": RAHUL[1]}, headers={**service, "X-Student-Session": student})
    assert r.status_code == 422
    r = await client.post(url, json={"bogus": 1}, headers={**service, "X-Student-Session": student})
    assert r.status_code == 422 and "Traceback" not in r.text and "unexpected keyword" not in r.text


async def test_skill_tools_disabled_without_configured_token(client, db, monkeypatch):
    monkeypatch.setattr(settings, "SKILL_SERVICE_TOKEN", None)
    r = await client.post("/v1/skill/tools/get_payments", json={}, headers={"X-Service-Token": "x" * 40})
    assert r.status_code == 503


async def test_public_key_endpoint_is_open(client):
    r = await client.get("/v1/attestations/public-key")
    assert r.status_code == 200 and r.json()["keys"][0]["kty"] == "OKP"
