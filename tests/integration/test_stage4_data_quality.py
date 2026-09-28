"""Stage 4 of production hardening (docs/LOGIC_AUDIT.md L18-L21, L27): data quality and robustness."""

from datetime import date

from sqlalchemy import select

from app.adapters.models import ParkedEvent
from app.adapters.sync_service import AdapterSyncService
from app.eligibility.service import current_academic_year
from app.ledger.models import Application, LedgerEvent
from app.ledger.service import LedgerService
from app.shared.types import CanonicalState, Gender, SchemeType, UserRole
from app.students.models import Student
from app.verification.sources import SourceClient
from tests.conftest import bearer, latest_sms_code, login, make_student, make_user, mocks_data

NSP_APP = "NSP-JH-2026-00417"
ME = {"full_name": "Mina Murmu", "dob": "2009-06-02", "gender": "FEMALE"}


async def _register(client, db, phone, **place):
    await client.post("/v1/auth/register/start", json={"phone": phone})
    r = await client.post("/v1/auth/register/complete", json={
        "phone": phone, "otp": await latest_sms_code(db, phone), **ME, **place})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── L21: place names ─────────────────────────────────────────────────────────

async def test_typed_place_names_still_reach_the_right_officers(client, db, demo, users):
    token = await _register(client, db, "9000000444", state="jharkhand", district="  dumka ")
    student = (await db.execute(select(Student).where(Student.full_name == "Mina Murmu"))).scalar_one()
    assert (student.state, student.district) == ("Jharkhand", "Dumka")
    app_id = (await client.post("/v1/applications", headers=token, json={
        "scheme": "PRE_MATRIC", "academic_year": current_academic_year()})).json()["id"]
    for who in ("district", "state"):
        ids = {a["id"] for a in (await client.get("/v1/applications", headers=await users.headers(who))).json()}
        assert app_id in ids, who


async def test_served_districts_come_from_officer_jurisdictions(client, demo, users):
    body = (await client.get("/v1/geo/districts")).json()
    assert {"state": "Jharkhand", "districts": ["Dumka"]} in body["states"]


# ── L20: the same person registering twice ───────────────────────────────────

async def test_a_second_registration_of_the_same_person_blocks_sanction(client, db, demo, users):
    year = current_academic_year()
    first = await _register(client, db, "9000000661", state="Jharkhand", district="Dumka")
    await client.post("/v1/applications", headers=first, json={"scheme": "PRE_MATRIC", "academic_year": year})
    second = await _register(client, db, "9000000662", state="Jharkhand", district="Dumka")
    r = await client.post("/v1/applications", headers=second, json={"scheme": "PRE_MATRIC", "academic_year": year})
    assert r.status_code == 201
    app_id = r.json()["id"]
    assert any(f.startswith("POSSIBLE_DUPLICATE_OF:") for f in r.json()["provisional_flags"])
    ledger = LedgerService(db)
    app = await db.get(Application, app_id)
    for s in (CanonicalState.INSTITUTE_VERIFICATION, CanonicalState.AUTHORITY_VERIFICATION):
        await ledger.transition(app, s, "system:t")
    await db.commit()
    r = await client.post(f"/v1/officer/applications/{app_id}/sanction", headers=await users.headers("district"), json={
        "instalments": [{"description": "Ad-hoc grant", "amount": 1000, "component": "adhoc_grant"}]})
    assert r.status_code == 422
    assert any("duplicate" in v for v in r.json()["detail"]["violations"])


# ── L18, L19: portal sync ────────────────────────────────────────────────────

async def _sync_all(db, gov):
    client = SourceClient("http://mocks", transport=gov.transport)
    try:
        return await AdapterSyncService(db, client).sync_all()
    finally:
        await client.aclose()


def _portal(app_id, aadhaar, **fields):
    return {"app_id": app_id, "aadhaar_ref": aadhaar, "scheme": "POST_MATRIC", "academic_year": "2026-27",
            "status": "PENDING_INSTITUTE", "status_updated_at": "2026-09-10T10:00:00+05:30",
            "submitted_at": "2026-09-05T10:00:00+05:30", "remarks": "", "payments": [], **fields}


async def test_one_malformed_record_is_parked_and_the_rest_still_sync(db, demo, gov):
    mocks_data.PORTAL_APPS["nsp"]["NSP-BAD-1"] = _portal("NSP-BAD-1", "AREF-JH-0004912", scheme="SOMETHING_NEW")
    results = await _sync_all(db, gov)
    imported = [(await db.get(Application, a)).source_ref for r in results for a in r.imported]
    assert NSP_APP in imported  # Salkhan's valid record synced despite Sunita's malformed one
    parked = (await db.execute(select(ParkedEvent).where(ParkedEvent.source_ref == "NSP-BAD-1"))).scalar_one()
    assert "SOMETHING_NEW" in parked.reason


async def test_skipped_stages_are_marked_as_inferred(db, demo, gov):
    mocks_data.PORTAL_APPS["nsp"][NSP_APP]["status"] = "PENDING_STATE_NODAL"
    await _sync_all(db, gov)
    app = (await db.execute(select(Application).where(Application.source_ref == NSP_APP))).scalar_one()
    events = (await db.execute(select(LedgerEvent).where(LedgerEvent.application_id == app.id)
                               .order_by(LedgerEvent.sequence_no))).scalars().all()
    marks = {e.type: e.payload.get("inferred") for e in events if "inferred" in e.payload}
    assert marks == {"InstituteVerificationStarted": True, "AuthorityVerificationStarted": False}


async def test_a_portal_copy_of_an_existing_application_is_parked_not_duplicated(db, demo, gov):
    year = "2026-27"
    ledger = LedgerService(db)
    own = await ledger.create_application("stu-salkhan-003", SchemeType.POST_MATRIC, year, "system:t")
    own_id = own.id
    await db.commit()
    await _sync_all(db, gov)
    apps = (await db.execute(select(Application).where(Application.student_id == "stu-salkhan-003"))).scalars().all()
    assert [a.id for a in apps] == [own_id]
    parked = (await db.execute(select(ParkedEvent).where(ParkedEvent.source_ref == NSP_APP))).scalar_one()
    assert "Possible duplicate" in parked.reason and parked.application_id == own_id


async def test_an_unknown_instalment_is_parked(db, demo, gov):
    portal = mocks_data.PORTAL_APPS["nsp"][NSP_APP]
    portal["status"] = "PAYMENT_SUCCESS"
    portal["payments"] = [{"instalment": 1, "description": "Maintenance", "amount": 6000,
                           "status": "PAYMENT_SUCCESS", "txn_ref": "T1"}]
    await _sync_all(db, gov)  # sanctioned with one instalment, credited
    portal["payments"].append({"instalment": 2, "description": "Mystery", "amount": 9999,
                               "status": "PAYMENT_SUCCESS", "txn_ref": "T2"})
    await _sync_all(db, gov)
    reasons = (await db.execute(select(ParkedEvent.reason).where(ParkedEvent.source_ref == NSP_APP))).scalars().all()
    assert any("instalment 2" in r and "not in the sanctioned plan" in r for r in reasons)


# ── L27: analytics stay inside the officer's state ───────────────────────────

async def test_state_officers_see_only_their_state(client, db, demo, users):
    await make_student(db, id="stu-odisha-1", full_name="Sukurmani Marandi", name_variants=[], dob=date(2011, 1, 5),
                       gender=Gender.FEMALE, state="Odisha", district="Mayurbhanj")
    ledger = LedgerService(db)
    prev = f"{int(current_academic_year()[:4]) - 1}-{current_academic_year()[2:4]}"
    await ledger.create_application("stu-odisha-1", SchemeType.PRE_MATRIC, prev, "system:t")
    await db.commit()
    state_rows = (await client.get("/v1/analytics/transitions", headers=await users.headers("state"))).json()
    ministry_rows = (await client.get("/v1/analytics/transitions", headers=await users.headers("ministry"))).json()
    assert "Mayurbhanj" not in {r["district"] for r in state_rows}
    assert "Mayurbhanj" in {r["district"] for r in ministry_rows}
    await make_user(db, "9000000071", UserRole.STATE_OFFICER, "Odisha officer", jurisdiction=("odisha ", None))
    odisha = bearer(await login(client, db, "9000000071"))
    assert {r["district"] for r in (await client.get("/v1/analytics/transitions", headers=odisha)).json()} == {"Mayurbhanj"}
