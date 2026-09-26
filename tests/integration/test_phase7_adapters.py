"""Phase 7 (C6): portal adapters import and advance applications, and park what they cannot map."""

import importlib

from sqlalchemy import select

from app.adapters.models import ParkedEvent
from app.adapters.portal import StateMap, default_adapters
from app.adapters.sync_service import AdapterSyncService, shortest_path
from app.ledger.models import Application, LedgerEvent
from app.ledger.service import LedgerService
from app.shared.types import CanonicalState, SourceSystem
from app.students.models import Student
from app.verification.sources import SourceClient
from tests.conftest import mocks_data

NSP_APP = "NSP-JH-2026-00417"


async def _sync(db, gov):
    client = SourceClient("http://mocks", transport=gov.transport)
    try:
        return await AdapterSyncService(db, client).sync_student(await db.get(Student, "stu-salkhan-003"))
    finally:
        await client.aclose()


def test_all_adapters_import_and_use_the_right_sources():
    for module in ("app.adapters.portal", "app.adapters.sync_service", "app.adapters.router"):
        importlib.import_module(module)
    assert [a.source for a in default_adapters()] == [SourceSystem.NSP, SourceSystem.SFMP, SourceSystem.NOS_PORTAL]
    for folder in ("nsp", "sfmp", "nos"):
        assert StateMap.load(folder).state("SOMETHING_NEW") is None  # unknown is never mapped to DRAFT


def test_shortest_path_walks_the_state_machine():
    assert shortest_path(CanonicalState.SUBMITTED, CanonicalState.SANCTIONED) == [
        CanonicalState.INSTITUTE_VERIFICATION, CanonicalState.AUTHORITY_VERIFICATION, CanonicalState.SANCTIONED]
    assert shortest_path(CanonicalState.REJECTED, CanonicalState.SANCTIONED) is None


async def test_nsp_application_is_imported_with_source_attribution(db, demo, gov):
    result = await _sync(db, gov)
    assert len(result.imported) == 1 and result.parked == 0
    app = (await db.execute(select(Application).where(Application.source_ref == NSP_APP))).scalar_one()
    assert app.source_system == SourceSystem.NSP and app.canonical_state == CanonicalState.INSTITUTE_VERIFICATION
    events = (await db.execute(select(LedgerEvent).where(LedgerEvent.application_id == app.id)
                               .order_by(LedgerEvent.sequence_no))).scalars().all()
    assert [e.type for e in events] == ["ApplicationCreated", "InstituteVerificationStarted"]
    assert {e.actor for e in events} == {"source:NSP"} and {e.source for e in events} == {SourceSystem.NSP}
    assert (await _sync(db, gov)).imported == []  # idempotent


async def test_portal_progress_including_payments_reaches_the_ledger(db, demo, gov):
    await _sync(db, gov)
    portal_app = mocks_data.PORTAL_APPS["nsp"][NSP_APP]
    portal_app["status"] = "PAYMENT_SUCCESS"
    portal_app["payments"] = [{"instalment": 1, "description": "Maintenance allowance", "amount": 6000,
                               "status": "PAYMENT_SUCCESS", "txn_ref": "NSP-TXN-1"}]
    result = await _sync(db, gov)
    assert result.parked == 0 and result.transitions == 2 and result.payments_updated == 2
    app = (await db.execute(select(Application).where(Application.source_ref == NSP_APP))).scalar_one()
    assert app.canonical_state == CanonicalState.CREDITED
    money = await LedgerService(db).money_view("stu-salkhan-003")
    assert money["total_credited"] == 6000
    assert (await LedgerService(db).verify_chain(app.id)).valid


async def test_unknown_status_is_parked_and_alerted_not_guessed(client, db, demo, users, gov):
    await _sync(db, gov)
    mocks_data.PORTAL_APPS["nsp"][NSP_APP]["status"] = "SENT_BACK_FOR_AADHAAR_REVALIDATION"
    result = await _sync(db, gov)
    assert result.parked == 1
    app = (await db.execute(select(Application).where(Application.source_ref == NSP_APP))).scalar_one()
    assert app.canonical_state == CanonicalState.INSTITUTE_VERIFICATION  # unchanged, not DRAFT
    parked = (await db.execute(select(ParkedEvent))).scalar_one()
    assert parked.raw_status == "SENT_BACK_FOR_AADHAAR_REVALIDATION" and "Unknown NSP status" in parked.reason
    assert (await _sync(db, gov)).parked == 0  # alerted once, not on every poll
    listed = (await client.get("/v1/admin/adapters/parked", headers=await users.headers("district"))).json()
    assert [p["source_ref"] for p in listed] == [NSP_APP]


async def test_impossible_jump_is_parked(db, demo, gov):
    await _sync(db, gov)
    mocks_data.PORTAL_APPS["nsp"][NSP_APP]["status"] = "DRAFT_SAVED"  # cannot go back to draft
    assert (await _sync(db, gov)).parked == 1


async def test_portal_outage_is_reported_not_fatal(db, demo, gov):
    gov.down.add("/nsp")
    result = await _sync(db, gov)
    assert result.imported == [] and any("NSP" in e for e in result.errors)
