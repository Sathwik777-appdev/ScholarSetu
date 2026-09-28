"""DigiLocker partner flow against the test DigiLocker (mocks/digilocker): OAuth 2.0 + PKCE, import, labels.

A document from a mock or sandbox DigiLocker is test data: it is stored as DIGILOCKER_TEST, never issuer-signed,
never shown as verified, and does not count as proof in verification outside DEMO_MODE."""

from datetime import date
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from sqlalchemy import select

from app.config import settings
from app.digilocker.models import DigiLockerSession
from app.digilocker.router import get_digilocker_http
from app.main import app
from app.shared.types import ClaimType, VerificationStatus
from app.verification.plugins.base import SubjectRef
from app.verification.plugins.digilocker_verifier import DigiLockerVerifier
from app.verification.sources import SourceClient
from app.wallet.models import WalletDocument
from app.wallet.service import digilocker_source, to_response

CLIENT_ID, CLIENT_SECRET = "scholarsetu-test", "test-client-secret-0123456789abcdef"


@pytest.fixture
def digilocker(gov, monkeypatch):
    """The core's DigiLocker client pointed at the in-process test DigiLocker, with a registered client."""
    monkeypatch.setenv("DIGILOCKER_CLIENT_ID", CLIENT_ID)          # read by the mock
    monkeypatch.setenv("DIGILOCKER_CLIENT_SECRET", CLIENT_SECRET)
    monkeypatch.setattr(settings, "DIGILOCKER_MODE", "mock")
    monkeypatch.setattr(settings, "DIGILOCKER_CLIENT_ID", CLIENT_ID)
    monkeypatch.setattr(settings, "DIGILOCKER_CLIENT_SECRET", CLIENT_SECRET)

    async def _http():
        async with httpx.AsyncClient(base_url="http://mocks/digilocker", transport=gov.transport) as c:
            yield c

    app.dependency_overrides[get_digilocker_http] = _http
    yield gov
    app.dependency_overrides.pop(get_digilocker_http, None)


def _local(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.path}?{parts.query}"


async def _sign_in(client, headers, mobile="9876543210", otp="123456") -> tuple[str, httpx.Response]:
    """Connect, open the (proxied) sign-in page, submit it. Returns the session id and the submit response."""
    r = await client.post("/v1/me/digilocker/connect", headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["label"] == "DigiLocker (test)" and body["test_service"] is True
    query = parse_qs(urlsplit(body["authorize_url"]).query)
    assert query["code_challenge_method"] == ["S256"] and query["client_id"] == [CLIENT_ID]
    assert query["redirect_uri"] == [settings.digilocker_redirect_uri]
    page = await client.get(_local(body["authorize_url"]))
    assert page.status_code == 200 and "TEST SERVICE" in page.text and "Sign in to DigiLocker (test)" in page.text
    form = {k: v[0] for k, v in query.items()} | {"mobile": mobile, "otp": otp}
    submit = await client.post(_local(body["authorize_url"]), data=form)
    return body["session_id"], submit


async def test_full_flow_imports_test_documents_labelled_and_unverified(client, db, users, store, digilocker):
    headers = await users.headers("sunita")
    session_id, submit = await _sign_in(client, headers)
    assert submit.status_code == 302
    location = submit.headers["location"]
    assert location.startswith(settings.digilocker_redirect_uri) and "code=" in location

    done = await client.get(_local(location))
    assert done.status_code == 200 and "DigiLocker connected" in done.text
    # The one-time state cannot be replayed.
    again = await client.get(_local(location))
    assert again.status_code == 400 and "expired or was already used" in again.text

    r = await client.get(f"/v1/me/digilocker/sessions/{session_id}", headers=headers)
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["status"] == "CONNECTED" and s["digilocker_name"] == "Sunita Hansda" and s["label"] == "DigiLocker (test)"
    uris = {d["doctype"]: d["uri"] for d in s["documents"]}
    assert set(uris) == {"MARKSHEET_10", "INCOME_CERTIFICATE", "DOMICILE_CERTIFICATE"}
    assert s["documents"][0]["issuer"] and not any(d["already_imported"] for d in s["documents"])

    r = await client.post(f"/v1/me/digilocker/sessions/{session_id}/import", headers=headers,
                          json={"uris": [uris["INCOME_CERTIFICATE"], uris["MARKSHEET_10"]]})
    assert r.status_code == 201, r.text
    imported = r.json()["imported"]
    assert [d["document_type"] for d in imported] == ["INCOME_CERTIFICATE", "MARKSHEET_10"]
    for d in imported:
        assert d["source"] == "DIGILOCKER_TEST" and d["source_label"] == "DigiLocker (test)"
        assert d["test_document"] is True and d["verified"] is False and d["mime_type"] == "application/pdf"
        assert d["title"].endswith("[test]")
    stored = store.objects[f"students/{imported[0]['student_id']}/{imported[0]['id']}"]
    assert stored.startswith(b"%PDF-") and b"TEST DOCUMENT - NOT VALID" in stored

    db.expire_all()
    rows = (await db.execute(select(WalletDocument))).scalars().all()
    assert len(rows) == 2 and not any(row.issuer_signed for row in rows)
    session = await db.get(DigiLockerSession, session_id)
    assert session.status == "DONE" and session.access_token is None  # the token is discarded

    wallet = (await client.get("/v1/me/wallet", headers=headers)).json()
    assert {d["source_label"] for d in wallet["documents"]} == {"DigiLocker (test)"}
    assert not any(d["verified"] for d in wallet["documents"])


async def test_wrong_code_on_sign_in_page_is_refused(client, users, digilocker):
    headers = await users.headers("sunita")
    _, submit = await _sign_in(client, headers, otp="000000")
    assert submit.status_code == 401 and "Could not sign in" in submit.text


async def test_tampered_pkce_verifier_fails_token_exchange(client, db, users, digilocker):
    headers = await users.headers("sunita")
    session_id, submit = await _sign_in(client, headers)
    session = await db.get(DigiLockerSession, session_id)
    session.code_verifier = "x" * 64  # no longer matches the challenge sent to DigiLocker
    await db.commit()
    r = await client.get(_local(submit.headers["location"]))
    assert r.status_code == 400 and "refused the sign-in (HTTP 400)" in r.text
    db.expire_all()
    session = await db.get(DigiLockerSession, session_id)
    assert session.status == "FAILED" and session.access_token is None
    r = await client.get(f"/v1/me/digilocker/sessions/{session_id}", headers=headers)
    assert r.json()["status"] == "FAILED" and r.json()["documents"] == []


async def test_import_refuses_documents_not_issued_to_the_student(client, users, store, digilocker):
    headers = await users.headers("sunita")
    session_id, submit = await _sign_in(client, headers)
    await client.get(_local(submit.headers["location"]))
    r = await client.post(f"/v1/me/digilocker/sessions/{session_id}/import", headers=headers,
                          json={"uris": ["in.gov.other-FAKE-1"]})
    assert r.status_code == 422 and "in.gov.other-FAKE-1" in r.json()["detail"]


async def test_another_student_cannot_read_the_session(client, users, digilocker):
    session_id, _ = await _sign_in(client, await users.headers("sunita"))
    r = await client.get(f"/v1/me/digilocker/sessions/{session_id}", headers=await users.headers("rahul"))
    assert r.status_code == 404


async def test_connect_is_refused_when_not_configured(client, users, digilocker, monkeypatch):
    monkeypatch.setattr(settings, "DIGILOCKER_CLIENT_SECRET", None)
    r = await client.post("/v1/me/digilocker/connect", headers=await users.headers("sunita"))
    assert r.status_code == 503 and "not configured" in r.json()["detail"]


async def test_test_sign_in_page_is_not_served_outside_mock_mode(client, digilocker, monkeypatch):
    monkeypatch.setattr(settings, "DIGILOCKER_MODE", "production")
    assert (await client.get("/v1/digilocker-test/authorize?state=x")).status_code == 404
    assert (await client.post("/v1/digilocker-test/authorize", data={"state": "x"})).status_code == 404


@pytest.mark.parametrize("mode", ["mock", "sandbox"])
def test_test_digilocker_documents_are_never_issuer_signed(mode, monkeypatch):
    monkeypatch.setattr(settings, "DIGILOCKER_MODE", mode)
    assert digilocker_source() == ("DIGILOCKER_TEST", False)
    monkeypatch.setattr(settings, "DIGILOCKER_MODE", "production")
    assert digilocker_source() == ("DIGILOCKER", True)


def test_a_test_document_cannot_appear_issuer_signed_even_if_the_row_says_so():
    from datetime import datetime, timezone
    doc = WalletDocument(id="d1", student_id="s1", document_type="MARKSHEET_10", title="t", source="DIGILOCKER_TEST",
                         source_ref="u", storage_key="k", mime_type="application/pdf", size_bytes=1,
                         content_sha256="0" * 64, issuer_signed=True, created_at=datetime.now(timezone.utc))
    out = to_response(doc)
    assert out.verified is False and out.test_document is True and out.source_label == "DigiLocker (test)"


def _sunita_subject() -> SubjectRef:
    return SubjectRef(student_id="stu-sunita-001", aadhaar_ref="AREF-JH-0004912", apaar_id=None,
                      nta_roll_number=None, name="Sunita Hansda", name_variants=["Sunita Hansda"],
                      dob=date(2008, 4, 12), gender="FEMALE", father_name="Babulal Hansda", mother_name=None,
                      district="Dumka")


@pytest.mark.parametrize("mode,demo,included", [("mock", True, True), ("mock", False, False),
                                                ("sandbox", True, False), ("production", True, False)])
def test_digilocker_lookup_takes_part_in_verification_only_in_the_demo(mode, demo, included, monkeypatch):
    from app.verification.service import default_plugins
    monkeypatch.setattr(settings, "DIGILOCKER_MODE", mode)
    monkeypatch.setattr(settings, "DEMO_MODE", demo)
    assert any(isinstance(p, DigiLockerVerifier) for p in default_plugins()) is included


async def test_test_digilocker_is_not_proof_outside_demo_mode(gov, monkeypatch):
    monkeypatch.setattr(settings, "DIGILOCKER_MODE", "mock")
    client = SourceClient("http://mocks", transport=gov.transport)
    try:
        monkeypatch.setattr(settings, "DEMO_MODE", False)
        result = await DigiLockerVerifier().verify(ClaimType.ACADEMIC_RECORDS, _sunita_subject(), None, client)
        assert result.status == VerificationStatus.MANUAL_REVIEW
        assert result.reasons == ["The test DigiLocker is not accepted as proof outside demo mode"]

        monkeypatch.setattr(settings, "DEMO_MODE", True)
        result = await DigiLockerVerifier().verify(ClaimType.ACADEMIC_RECORDS, _sunita_subject(), None, client)
        assert result.status == VerificationStatus.VERIFIED
        assert "test DigiLocker" in result.reasons[0] and "not issuer-signed" in result.reasons[0]
    finally:
        await client.aclose()
