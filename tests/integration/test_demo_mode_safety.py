"""Demo mode must never weaken security or invent data (docs/LOGIC_AUDIT.md L1-L7, L9).

The rest of the suite runs with DEMO_MODE off; these tests switch it on, because that is where the
shortcuts that were found in the audit lived."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import Settings, settings
from app.shared.types import UserRole
from tests.conftest import PHONES, bearer, login, make_user


@pytest.fixture(autouse=True)
def demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", True)


async def test_no_unsigned_demo_tokens(client, demo):
    r = await client.get("/v1/analytics/overview", headers={"Authorization": "Bearer demo-token-9876543240"})
    assert r.status_code == 401


async def test_an_invalid_token_is_never_someone_else(client, demo):
    assert (await client.get("/v1/me/dashboard", headers={"Authorization": "Bearer not-a-jwt"})).status_code == 401


async def test_expired_tokens_are_refused(client, db, demo):
    claims = jwt.decode(await login(client, db, PHONES["district"]), settings.JWT_SECRET, algorithms=["HS256"])
    claims["exp"] = int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
    expired = jwt.encode(claims, settings.JWT_SECRET, algorithm="HS256")
    assert (await client.get("/v1/analytics/overview", headers=bearer(expired))).status_code == 401


async def test_the_demo_code_is_only_for_seeded_demo_users(client, db, demo):
    unknown = await client.post("/v1/auth/otp/verify", json={"phone": "9123456789", "otp": settings.DEMO_OTP})
    assert unknown.status_code == 401
    await make_user(db, "9000000999", UserRole.MINISTRY, "Real ministry user", is_demo=False)
    real = await client.post("/v1/auth/otp/verify", json={"phone": "9000000999", "otp": settings.DEMO_OTP})
    assert real.status_code == 401


async def test_registration_always_confirms_the_phone(client, demo):
    r = await client.post("/v1/auth/register/complete", json={
        "phone": "9000000555", "otp": settings.DEMO_OTP, "full_name": "Someone Else", "dob": "2009-01-01",
        "gender": "MALE", "state": "Jharkhand", "district": "Dumka"})
    assert r.status_code == 401


def test_safe_defaults():
    fields = Settings.model_fields
    assert fields["DEMO_MODE"].default is False
    assert fields["JWT_EXPIRE_MINUTES"].default <= 60
    assert fields["OTP_TTL_MINUTES"].default <= 10


async def test_empty_wallet_and_passport_stay_empty(client, demo, users, store):
    rahul = await users.headers("rahul")
    wallet = (await client.get("/v1/me/wallet", headers=rahul)).json()
    passport = (await client.get("/v1/me/attestations", headers=rahul)).json()
    assert wallet["documents"] == [] and wallet["total_documents"] == 0
    assert all(v == [] for v in passport["attestations"].values())


async def test_coverage_is_unavailable_not_invented_when_udise_is_down(client, demo, users, gov):
    gov.down.add("/udise")
    r = await client.get("/v1/analytics/coverage", headers=await users.headers("ministry"))
    assert r.status_code == 503
