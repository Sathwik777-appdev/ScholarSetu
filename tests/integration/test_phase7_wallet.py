"""Phase 7: wallet documents in object storage; DigiLocker pulls need consent; reads are scoped and audited."""

from sqlalchemy import select

from app.gateway.models import AuditLog
from tests.conftest import grant_consent

PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


async def _pull(client, headers, consent_id, doc_type="MARKSHEET_10"):
    return await client.post("/v1/me/wallet/digilocker/pull", headers=headers,
                             json={"doc_type": doc_type, "consent_id": consent_id})


async def test_digilocker_pull_needs_a_wallet_consent(client, users, gov, store):
    sunita = await users.headers("sunita")
    assert (await _pull(client, sunita, "none")).status_code == 403
    wrong = await grant_consent(client, sunita, ["INCOME"])  # verification consent, not a wallet one
    assert (await _pull(client, sunita, wrong)).status_code == 403
    assert store.objects == {}


async def test_digilocker_pull_stores_the_issued_document_once(client, users, gov, store):
    sunita = await users.headers("sunita")
    consent = await grant_consent(client, sunita, ["DIGILOCKER:MARKSHEET_10"], requester="SCHOLARSETU_WALLET")
    r = await _pull(client, sunita, consent)
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["verified"] is True and doc["mime_type"] == "application/pdf" and doc["source"] == "DIGILOCKER"
    assert doc["digilocker_uri"] == "in.gov.jac-MARKSHEET_10-2026-109283"
    [stored] = store.objects.values()
    assert stored.startswith(b"%PDF-") and b"SUNITA HANSDA" in stored
    assert (await _pull(client, sunita, consent)).json()["id"] == doc["id"]  # deduplicated
    wallet = (await client.get("/v1/me/wallet", headers=sunita)).json()
    assert wallet["total_documents"] == 1

    content = await client.get(f"/v1/wallet/documents/{doc['id']}/content", headers=sunita)
    assert content.status_code == 200 and content.content == stored
    assert content.headers["content-type"] == "application/pdf"


async def test_missing_digilocker_document_is_404(client, users, gov, store):
    rahul = await users.headers("rahul")
    consent = await grant_consent(client, rahul, ["DIGILOCKER:MARKSHEET_10"], requester="SCHOLARSETU_WALLET")
    assert (await _pull(client, rahul, consent)).status_code == 404


async def test_upload_checks_content_not_name(client, users, store):
    sunita = await users.headers("sunita")
    ok = await client.post("/v1/me/wallet/documents", headers=sunita,
                           data={"document_type": "INCOME_CERTIFICATE", "title": "Income certificate FY 2026-27"},
                           files={"file": ("income.pdf", PDF, "application/pdf")})
    assert ok.status_code == 201 and ok.json()["verified"] is False and ok.json()["mime_type"] == "application/pdf"
    fake = await client.post("/v1/me/wallet/documents", headers=sunita,
                             data={"document_type": "INCOME_CERTIFICATE", "title": "Not really a PDF"},
                             files={"file": ("income.pdf", b"MZ\x90\x00 executable", "application/pdf")})
    assert fake.status_code == 415


async def test_upload_size_limit(client, users, store, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "WALLET_MAX_UPLOAD_BYTES", 32)
    r = await client.post("/v1/me/wallet/documents", headers=await users.headers("sunita"),
                          data={"document_type": "INCOME_CERTIFICATE", "title": "Too big"},
                          files={"file": ("big.pdf", PDF + b"x" * 100, "application/pdf")})
    assert r.status_code == 413


async def test_document_reads_are_scoped_and_audited(client, db, users, store):
    sunita = await users.headers("sunita")
    doc_id = (await client.post("/v1/me/wallet/documents", headers=sunita,
                                data={"document_type": "INCOME_CERTIFICATE", "title": "Income certificate"},
                                files={"file": ("i.pdf", PDF, "application/pdf")})).json()["id"]
    url = f"/v1/wallet/documents/{doc_id}/content"
    assert (await client.get(url, headers=await users.headers("rahul"))).status_code == 404
    assert (await client.get(url, headers=await users.headers("district"))).status_code == 200  # Dumka officer
    reads = (await db.execute(select(AuditLog).where(AuditLog.action == "WALLET_DOCUMENT_READ"))).scalars().all()
    assert len(reads) == 1 and reads[0].actor_role == "DISTRICT_OFFICER"


async def test_tampered_bytes_fail_the_integrity_check(client, users, store):
    sunita = await users.headers("sunita")
    doc_id = (await client.post("/v1/me/wallet/documents", headers=sunita,
                                data={"document_type": "INCOME_CERTIFICATE", "title": "Income certificate"},
                                files={"file": ("i.pdf", PDF, "application/pdf")})).json()["id"]
    key = next(iter(store.objects))
    store.objects[key] = PDF.replace(b"1 0 obj", b"9 9 obj")
    assert (await client.get(f"/v1/wallet/documents/{doc_id}/content", headers=sunita)).status_code == 500


async def test_upload_queued_offline_is_stored_once(client, users, store, db):
    from sqlalchemy import func, select
    from app.wallet.models import WalletDocument
    sunita = {**await users.headers("sunita"), "Idempotency-Key": "dev1-upload-0001"}
    form = {"document_type": "INCOME_CERT", "title": "Income certificate 2026-27"}
    first = await client.post("/v1/me/wallet/documents", headers=sunita, data=form,
                              files={"file": ("income.pdf", PDF, "application/pdf")})
    again = await client.post("/v1/me/wallet/documents", headers=sunita, data=form,
                              files={"file": ("income.pdf", PDF, "application/pdf")})
    assert first.status_code == 201 and again.status_code == 200
    assert again.json()["id"] == first.json()["id"] and first.json()["verified"] is False  # self-uploaded
    assert await db.scalar(select(func.count()).select_from(WalletDocument)
                           .where(WalletDocument.document_type == "INCOME_CERT")) == 1
