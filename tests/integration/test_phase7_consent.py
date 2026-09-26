"""Phase 7 (S3): consents are persisted, enforced on every data pull, and revocable."""

from sqlalchemy import select

from app.gateway.models import AuditLog
from tests.conftest import grant_consent


async def _verify(client, headers, app_id, claims, consent_id):
    return await client.post("/v1/verify/claims", headers=headers,
                             json={"application_id": app_id, "required_claims": claims, "consent_id": consent_id})


async def test_verification_without_a_consent_is_403(client, demo, users, gov):
    r = await _verify(client, await users.headers("sunita"), demo["sunita_application"], ["INCOME"], "cst-auto-001")
    assert r.status_code == 403 and "No consent" in r.json()["detail"]
    assert gov.calls == []  # nothing was pulled


async def test_consent_must_cover_every_item(client, demo, users, gov):
    sunita = await users.headers("sunita")
    consent_id = await grant_consent(client, sunita, ["INCOME"])
    r = await _verify(client, sunita, demo["sunita_application"], ["INCOME", "ST_STATUS"], consent_id)
    assert r.status_code == 403 and "does not cover: ST_STATUS" in r.json()["detail"]


async def test_revoking_a_consent_blocks_the_next_verification(client, db, demo, users, gov):
    sunita = await users.headers("sunita")
    consent_id = await grant_consent(client, sunita, ["INCOME"])
    assert (await _verify(client, sunita, demo["sunita_application"], ["INCOME"], consent_id)).status_code == 200
    r = await client.delete(f"/v1/consents/{consent_id}", headers=sunita)
    assert r.status_code == 200 and r.json()["is_active"] is False
    r = await _verify(client, sunita, demo["sunita_application"], ["INCOME"], consent_id)
    assert r.status_code == 403 and "revoked" in r.json()["detail"]
    actions = (await db.execute(select(AuditLog.action))).scalars().all()
    assert {"CONSENT_GRANTED", "CONSENT_REVOKED"} <= set(actions)


async def test_revoking_unknown_or_someone_elses_consent_is_404(client, users):
    rahul_consent = await grant_consent(client, await users.headers("rahul"), ["INCOME"])
    sunita = await users.headers("sunita")
    assert (await client.delete("/v1/consents/does-not-exist", headers=sunita)).status_code == 404
    assert (await client.delete(f"/v1/consents/{rahul_consent}", headers=sunita)).status_code == 404


async def test_officer_verification_needs_the_students_consent(client, demo, users, gov):
    officer = await users.headers("district")
    r = await _verify(client, officer, demo["sunita_application"], ["INCOME"], "none")
    assert r.status_code == 403
    consent_id = await grant_consent(client, await users.headers("sunita"), ["INCOME"])
    assert (await _verify(client, officer, demo["sunita_application"], ["INCOME"], consent_id)).status_code == 200


async def test_consents_are_listed_and_validated(client, users):
    sunita = await users.headers("sunita")
    await grant_consent(client, sunita, ["INCOME", "ST_STATUS"])
    listed = (await client.get("/v1/me/consents", headers=sunita)).json()
    assert len(listed) == 1 and listed[0]["is_active"] and listed[0]["data_items"] == ["INCOME", "ST_STATUS"]
    bad = await client.post("/v1/consents", headers=sunita, json={
        "requester": "ANYONE", "purpose": "whatever", "data_items": ["INCOME"], "duration_days": 5})
    assert bad.status_code == 422
