"""Officer accounts: enrolled by the Ministry, sign in with an emailed code, never accept the demo code."""

from sqlalchemy import select

from app.config import settings
from app.gateway.models import AuditLog, OtpChallenge, User


async def _ministry(users):
    return await users.headers("ministry")


async def test_enrolment_needs_an_officer_role_and_a_jurisdiction(client, users):
    m = await _ministry(users)
    base = {"name": "Block Officer, Jama", "email": "Officer.Jama@Example.gov.in"}
    assert (await client.post("/v1/admin/officers", headers=m, json={**base, "role": "STUDENT"})).status_code == 422
    r = await client.post("/v1/admin/officers", headers=m, json={**base, "role": "DISTRICT_OFFICER",
                                                                 "jurisdiction_state": "Jharkhand"})
    assert r.status_code == 422 and "district" in r.json()["detail"]
    r = await client.post("/v1/admin/officers", headers=m, json={
        **base, "role": "DISTRICT_OFFICER", "jurisdiction_state": " jharkhand", "jurisdiction_district": "jama "})
    assert r.status_code == 201, r.text
    officer = r.json()
    assert officer["email"] == "officer.jama@example.gov.in" and officer["is_demo"] is False
    assert (officer["jurisdiction_state"], officer["jurisdiction_district"]) == ("Jharkhand", "Jama")
    again = await client.post("/v1/admin/officers", headers=m, json={**base, "role": "STATE_OFFICER",
                                                                     "jurisdiction_state": "Jharkhand"})
    assert again.status_code == 409
    listed = (await client.get("/v1/admin/officers", headers=m)).json()
    assert officer["id"] in {o["id"] for o in listed}
    assert (await client.get("/v1/admin/officers", headers=await users.headers("district"))).status_code == 403


async def test_an_enrolled_officer_signs_in_with_the_emailed_code_never_the_demo_code(client, db, users, monkeypatch):
    m = await _ministry(users)
    await client.post("/v1/admin/officers", headers=m, json={
        "name": "State Officer", "email": "state.officer@example.gov.in", "role": "STATE_OFFICER",
        "jurisdiction_state": "Jharkhand"})
    sent = []

    async def fake_send(to, otp):
        sent.append((to, otp))
        return True
    monkeypatch.setattr("app.gateway.email.send_login_code", fake_send)
    monkeypatch.setattr(settings, "DEMO_MODE", True)
    email = "State.Officer@example.gov.in"
    assert (await client.post("/v1/auth/otp/request", json={"email": email, "demo": True})).status_code == 202
    assert sent and sent[0][0] == "state.officer@example.gov.in"  # a real account gets a real code even via the toggle
    demo = await client.post("/v1/auth/otp/verify", json={"email": email, "otp": settings.DEMO_OTP, "demo": True})
    assert demo.status_code == 401
    ok = await client.post("/v1/auth/otp/verify", json={"email": email, "otp": sent[0][1]})
    assert ok.status_code == 200 and ok.json()["user"]["role"] == "STATE_OFFICER"
    assert (await db.execute(select(OtpChallenge).where(OtpChallenge.email == "state.officer@example.gov.in"))).scalar_one()


async def test_a_deactivated_officer_cannot_sign_in_or_keep_using_a_token(client, db, users):
    m = await _ministry(users)
    district = await users.headers("district")
    officer = (await db.execute(select(User).where(User.role == "DISTRICT_OFFICER"))).scalars().first()
    r = await client.post(f"/v1/admin/officers/{officer.id}/active", headers=m, json={"active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert (await client.get("/v1/applications", headers=district)).status_code == 401
    me = (await client.get("/v1/auth/me", headers=m)).json()
    assert (await client.post(f"/v1/admin/officers/{me['id']}/active", headers=m,
                              json={"active": False})).status_code == 409
    actions = {a.action for a in (await db.execute(select(AuditLog))).scalars()}
    assert "OFFICER_DEACTIVATED" in actions
