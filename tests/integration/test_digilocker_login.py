"""Sign in with DigiLocker: the only sign-in for real students (docs/ARCHITECTURE.md §19 row 49)."""

import httpx
from sqlalchemy import select

from app.config import settings
from app.digilocker.login import parse_dob
from app.digilocker.models import DigiLockerLogin
from app.digilocker.router import get_digilocker_http
from app.gateway.models import User
from app.main import app
from app.students.models import Student
from tests.conftest import digilocker_signup


async def test_a_new_person_signs_up_with_digilocker_and_then_signs_straight_in(client, db, monkeypatch):
    headers = await digilocker_signup(client, monkeypatch, "DL-1001", "SONI MURMU", "02062009", "F",
                                      state=" jharkhand", district="dumka ")
    me = (await client.get("/v1/auth/me", headers=headers)).json()
    assert me["role"] == "STUDENT" and me["name"] == "Soni Murmu"
    student = (await db.execute(select(Student).where(Student.id == me["student_id"]))).scalar_one()
    assert (str(student.dob), student.gender.value, student.state, student.district) == \
        ("2009-06-02", "FEMALE", "Jharkhand", "Dumka")  # identity from DigiLocker, places tidied
    user = (await db.execute(select(User).where(User.student_id == student.id))).scalar_one()
    assert user.digilocker_id == "DL-1001" and user.phone is None and user.is_demo is False
    # The same DigiLocker account next time: signed in, no second student.
    again = await digilocker_signup(client, monkeypatch, "DL-1001", "SONI MURMU", "02062009", "F")
    assert (await client.get("/v1/auth/me", headers=again)).json()["id"] == me["id"]
    assert len((await db.execute(select(Student).where(Student.full_name == "Soni Murmu"))).scalars().all()) == 1


async def _http_returning(status: int, body: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    async def _http():
        async with httpx.AsyncClient(base_url="http://digilocker", transport=httpx.MockTransport(handler)) as c:
            yield c
    return _http


async def test_state_is_single_use_and_a_refused_exchange_does_not_sign_in(client, db, monkeypatch):
    monkeypatch.setattr(settings, "DIGILOCKER_CLIENT_ID", "c")
    monkeypatch.setattr(settings, "DIGILOCKER_CLIENT_SECRET", "s" * 20)
    app.dependency_overrides[get_digilocker_http] = await _http_returning(400, {"error": "invalid_grant"})
    try:
        state = (await client.post("/v1/auth/digilocker/start")).json()["state"]
        r = await client.post("/v1/auth/digilocker/complete", json={"state": state, "code": "abcd1234"})
        assert r.status_code == 401
        r = await client.post("/v1/auth/digilocker/complete", json={"state": state, "code": "abcd1234"})
        assert r.status_code == 400 and "already used" in r.json()["detail"]
        assert (await client.post("/v1/auth/digilocker/complete",
                                  json={"state": "x" * 20, "code": "abcd"})).status_code == 400
    finally:
        app.dependency_overrides.pop(get_digilocker_http, None)
    assert (await db.execute(select(User))).scalars().all() == []


async def test_registration_token_is_single_use(client, db, monkeypatch):
    monkeypatch.setattr(settings, "DIGILOCKER_CLIENT_ID", "c")
    monkeypatch.setattr(settings, "DIGILOCKER_CLIENT_SECRET", "s" * 20)
    app.dependency_overrides[get_digilocker_http] = await _http_returning(
        200, {"access_token": "t", "digilockerid": "DL-2002", "name": "Ravi Hembrom", "dob": "01012008", "gender": "M"})
    try:
        state = (await client.post("/v1/auth/digilocker/start")).json()["state"]
        done = (await client.post("/v1/auth/digilocker/complete", json={"state": state, "code": "abcd1234"})).json()
        assert done["status"] == "NEEDS_SIGNUP" and done["profile"]["name"] == "Ravi Hembrom"
        body = {"registration_token": done["registration_token"], "state": "Jharkhand", "district": "Dumka"}
        assert (await client.post("/v1/auth/digilocker/register", json=body)).status_code == 201
        assert (await client.post("/v1/auth/digilocker/register", json=body)).status_code == 400
    finally:
        app.dependency_overrides.pop(get_digilocker_http, None)
    attempt = (await db.execute(select(DigiLockerLogin))).scalar_one()
    assert attempt.status == "DONE" and attempt.registration_token is None


async def test_not_configured_is_503(client, monkeypatch):
    monkeypatch.setattr(settings, "DIGILOCKER_CLIENT_SECRET", None)
    r = await client.post("/v1/auth/digilocker/start")
    assert r.status_code == 503 and "not configured" in r.json()["detail"]


def test_dates_as_digilocker_and_the_test_digilocker_send_them():
    assert str(parse_dob("12042008")) == "2008-04-12"
    assert str(parse_dob("2008-04-12")) == "2008-04-12"
    assert parse_dob("April 2008") is None and parse_dob(None) is None


async def test_full_flow_against_the_test_digilocker(client, db, demo, gov, monkeypatch):
    """The real partner flow (sign-in page, code, token exchange) against mocks/digilocker, returning to the app."""
    from urllib.parse import parse_qs, urlsplit
    monkeypatch.setenv("DIGILOCKER_CLIENT_ID", "scholarsetu-test")
    monkeypatch.setenv("DIGILOCKER_CLIENT_SECRET", "test-secret-0123456789")
    monkeypatch.setattr(settings, "DIGILOCKER_MODE", "mock")
    monkeypatch.setattr(settings, "DIGILOCKER_CLIENT_ID", "scholarsetu-test")
    monkeypatch.setattr(settings, "DIGILOCKER_CLIENT_SECRET", "test-secret-0123456789")

    async def _http():
        async with httpx.AsyncClient(base_url="http://mocks/digilocker", transport=gov.transport) as c:
            yield c
    app.dependency_overrides[get_digilocker_http] = _http
    try:
        start = (await client.post("/v1/auth/digilocker/start")).json()
        assert start["label"] == "DigiLocker (test)" and start["redirect_uri"] == "scholarsetu://digilocker-callback"
        query = {k: v[0] for k, v in parse_qs(urlsplit(start["authorize_url"]).query).items()}
        local = urlsplit(start["authorize_url"])
        submit = await client.post(f"{local.path}?{local.query}", data=query | {"mobile": "9876543213", "otp": "123456"})
        assert submit.status_code == 302 and submit.headers["location"].startswith("scholarsetu://digilocker-callback")
        code = parse_qs(urlsplit(submit.headers["location"]).query)["code"][0]
        done = (await client.post("/v1/auth/digilocker/complete", json={"state": start["state"], "code": code})).json()
        assert done["status"] == "NEEDS_SIGNUP" and done["profile"]["name"] == "Salkhan Soren"
    finally:
        app.dependency_overrides.pop(get_digilocker_http, None)
