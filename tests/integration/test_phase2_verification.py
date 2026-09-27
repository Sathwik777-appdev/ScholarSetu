"""Phase 2: verification fails closed (S5), review cases and officer decisions (M4)."""

import pytest
from sqlalchemy import func, select

from app.attestation.models import Attestation
from app.ledger.models import OutboxMessage
from app.shared.types import UserRole
from app.verification.models import ReviewCase
from tests.conftest import bearer, grant_consent, login, make_user

SUNITA_APP = RAHUL_APP = None  # set per test from the seeded demo world


@pytest.fixture
async def people(users, demo):
    global SUNITA_APP, RAHUL_APP
    SUNITA_APP, RAHUL_APP = demo["sunita_application"], demo["rahul_application"]
    return {"sunita": await users.token("sunita"), "rahul": await users.token("rahul"),
            "officer": await users.token("district")}


async def _verify(client, token, claims, app_id=None):
    app_id = app_id or SUNITA_APP
    consent_id = await grant_consent(client, bearer(token), claims)
    return await client.post("/v1/verify/claims", headers=bearer(token),
                             json={"application_id": app_id, "required_claims": claims, "consent_id": consent_id})


def _claims(report):
    return {c["claim_type"]: c for c in report["claims"]}


# ── fail closed ──────────────────────────────────────────────────────────────


async def test_every_source_down_gives_source_unavailable(client, db, people, gov):
    gov.down.add("*")
    r = await _verify(client, people["sunita"], ["IDENTITY", "ST_STATUS", "INCOME"])
    assert r.status_code == 200
    report = r.json()
    assert report["overall_status"] == "SOURCE_UNAVAILABLE"
    assert {c["status"] for c in report["claims"]} == {"SOURCE_UNAVAILABLE"}
    assert all(c["attestation_id"] is None and c["claim_value"] is None for c in report["claims"])
    # Every claim went to the review queue; nothing was attested.
    assert report["requires_manual_review"] and len(report["review_case_ids"]) == 3
    assert (await db.scalar(select(func.count()).select_from(Attestation))) == 0
    reasons = {c.reason.value for c in (await db.execute(select(ReviewCase))).scalars()}
    assert reasons == {"SOURCE_UNAVAILABLE"}


async def test_one_source_down_and_one_without_record_is_manual_review(client, people, gov):
    gov.down.add("/edistrict")  # DigiLocker answers (no caste certificate), e-District is down
    report = (await _verify(client, people["sunita"], ["ST_STATUS"])).json()
    st = _claims(report)["ST_STATUS"]
    assert st["status"] == "MANUAL_REVIEW" and report["overall_status"] == "MANUAL_REVIEW"
    assert {s["source"]: s["status"] for s in st["sources_consulted"]} == {
        "DigiLocker": "MANUAL_REVIEW", "e-District": "SOURCE_UNAVAILABLE"}


async def test_source_without_a_matching_record_is_never_verified(client, people, gov):
    # UDISE+ shows Sunita as PASSED_OUT of school, so current school enrolment is not confirmed.
    st = _claims((await _verify(client, people["sunita"], ["SCHOOL_ENROLMENT"])).json())["SCHOOL_ENROLMENT"]
    assert st["status"] == "MANUAL_REVIEW" and st["attestation_id"] is None and st["review_case_id"]
    assert "PASSED_OUT" in st["reasons"][0]


async def test_claim_without_any_verifier_goes_to_review(client, people, gov):
    st = _claims((await _verify(client, people["sunita"], ["DISABILITY"])).json())["DISABILITY"]
    assert st["status"] == "MANUAL_REVIEW" and gov.calls == []
    assert "No automated source" in st["reasons"][0]


async def test_unknown_student_is_404(client, db, people, gov):
    # A login linked to a student record that does not exist cannot apply or verify anything.
    await make_user(db, "9000000999", UserRole.STUDENT, "Random Student", student_id="stu-random-999")
    random_student = bearer(await login(client, db, "9000000999"))
    r = await client.post("/v1/applications", headers=random_student,
                          json={"scheme": "POST_MATRIC", "academic_year": "2026-27"})
    assert r.status_code == 404 and "stu-random-999" in r.json()["detail"]
    r = await client.post("/v1/verify/claims", headers=random_student,
                          json={"application_id": "APP-PM-2026-999999", "required_claims": ["IDENTITY"],
                                "consent_id": "c"})
    assert r.status_code == 404
    assert gov.calls == []


async def test_subject_comes_from_the_students_own_record(client, people, gov):
    report = (await _verify(client, people["rahul"], ["IDENTITY"], app_id=RAHUL_APP)).json()
    identity = _claims(report)["IDENTITY"]
    assert identity["status"] == "VERIFIED" and identity["claim_value"]["name"] == "Rahul Hansda"
    assert "/uidai/ekyc" in gov.calls


# ── confirmed claims ─────────────────────────────────────────────────────────


async def test_confirmed_claims_are_verified_and_then_reused(client, people, gov):
    report = (await _verify(client, people["sunita"], ["IDENTITY", "INCOME"])).json()
    claims = _claims(report)
    assert report["overall_status"] == "VERIFIED" and report["review_case_ids"] == []
    assert claims["IDENTITY"]["identity_decision"] == "AUTO_VERIFY"
    assert claims["INCOME"]["claim_value"]["annual_income"] == 120000
    assert claims["INCOME"]["attestation_status"] == "ACTIVE"

    gov.calls.clear()
    again = _claims((await _verify(client, people["sunita"], ["IDENTITY", "INCOME"])).json())
    assert gov.calls == []  # verify once, reuse everywhere
    assert "Reused attestation" in again["INCOME"]["reasons"][0]


# ── Hansda / Hansdah → review case ──────────────────────────────────────────


async def test_hansdah_certificate_opens_review_case_with_provisional_attestation(client, db, people, gov):
    report = (await _verify(client, people["sunita"], ["ST_STATUS"])).json()
    st = _claims(report)["ST_STATUS"]
    assert st["status"] == "PROVISIONAL" and report["overall_status"] == "PROVISIONAL"
    assert st["source"] == "e-District" and st["identity_decision"] == "PROVISIONAL"
    assert st["attestation_status"] == "PROVISIONAL" and st["claim_value"]["tribe"] == "Santal"
    assert "Sunita Hansdah" in st["reasons"][0] and "Sunita Hansda" in st["reasons"][0]

    cases = (await client.get("/v1/review/cases", headers=bearer(people["officer"]))).json()
    assert len(cases) == 1
    case = cases[0]
    assert case["id"] == st["review_case_id"] and case["claim_type"] == "ST_STATUS"
    assert case["reason"] == "IDENTITY_NOT_CONFIRMED" and case["status"] == "PENDING"
    assert case["attestation_id"] == st["attestation_id"] and case["student_name"] == "Sunita Hansda"
    assert {e["source"] for e in case["evidence_refs"]} == {"DigiLocker", "e-District"}

    db.expire_all()
    subjects = {m.subject for m in (await db.execute(select(OutboxMessage))).scalars()}
    assert {"verification.review_required", "verification.completed"} <= subjects

    # Repeating the verification does not open a second case.
    await _verify(client, people["sunita"], ["ST_STATUS"])
    assert len((await client.get("/v1/review/cases", headers=bearer(people["officer"]))).json()) == 1


# ── officer decisions ────────────────────────────────────────────────────────


async def _open_hansdah_case(client, people):
    st = _claims((await _verify(client, people["sunita"], ["ST_STATUS"])).json())["ST_STATUS"]
    return st["review_case_id"], st["attestation_id"]


async def _decide(client, people, case_id, decision, **extra):
    return await client.post(f"/v1/review/cases/{case_id}/decision", headers=bearer(people["officer"]),
                             json={"decision": decision, "notes": "Checked the certificate in person", **extra})


async def test_approve_activates_attestation_and_writes_ledger_event(client, people, gov):
    case_id, att_id = await _open_hansdah_case(client, people)
    r = await _decide(client, people, case_id, "APPROVE")
    assert r.status_code == 200
    body = r.json()
    assert body["case"]["status"] == "APPROVED" and body["attestation_status"] == "ACTIVE"

    timeline = (await client.get(f"/v1/applications/{SUNITA_APP}/timeline", headers=bearer(people["sunita"]))).json()
    event = next(e for e in timeline if e["event_id"] == body["ledger_event_id"])
    assert event["type"] == "ReviewDecisionRecorded"
    assert event["payload"]["decision"] == "APPROVE" and event["payload"]["review_case_id"] == case_id

    check = await client.get(f"/v1/attestations/{att_id}/verify", headers=bearer(people["sunita"]))
    assert check.json() == {"is_valid": True, "reason": None}

    # Approved attestation is now reused instead of re-verified.
    gov.calls.clear()
    st = _claims((await _verify(client, people["sunita"], ["ST_STATUS"])).json())["ST_STATUS"]
    assert st["status"] == "VERIFIED" and gov.calls == []

    assert (await _decide(client, people, case_id, "REJECT")).status_code == 409


async def test_reject_revokes_attestation(client, people, gov):
    case_id, att_id = await _open_hansdah_case(client, people)
    body = (await _decide(client, people, case_id, "REJECT")).json()
    assert body["case"]["status"] == "REJECTED" and body["attestation_status"] == "REVOKED"
    check = (await client.get(f"/v1/attestations/{att_id}/verify", headers=bearer(people["sunita"]))).json()
    assert check["is_valid"] is False and "REVOKED" in check["reason"]


async def test_request_info_keeps_case_open(client, people, gov):
    case_id, _ = await _open_hansdah_case(client, people)
    body = (await _decide(client, people, case_id, "REQUEST_INFO")).json()
    assert body["case"]["status"] == "INFO_REQUESTED" and body["attestation_status"] == "PROVISIONAL"
    assert (await _decide(client, people, case_id, "APPROVE")).json()["case"]["status"] == "APPROVED"


@pytest.mark.parametrize("bad", ["VERIFIED", "APPROVED", "SOURCE_UNAVAILABLE", "NEEDS_MORE_INFO"])
async def test_only_review_decisions_are_accepted(client, people, gov, bad):
    case_id, _ = await _open_hansdah_case(client, people)
    assert (await _decide(client, people, case_id, bad)).status_code == 422


async def test_approving_a_case_without_evidence_needs_a_value(client, people, gov):
    case_id = _claims((await _verify(client, people["sunita"], ["DISABILITY"])).json())["DISABILITY"]["review_case_id"]
    assert (await _decide(client, people, case_id, "APPROVE")).status_code == 422
    body = (await _decide(client, people, case_id, "APPROVE",
                          claim_value={"udid_no": "JH0420260001", "percentage": 45})).json()
    assert body["attestation_status"] == "ACTIVE"


async def test_students_cannot_decide(client, people, gov):
    case_id, _ = await _open_hansdah_case(client, people)
    r = await client.post(f"/v1/review/cases/{case_id}/decision", headers=bearer(people["sunita"]),
                          json={"decision": "APPROVE", "notes": "self approval"})
    assert r.status_code == 403


async def test_outage_case_closes_when_sources_recover(client, db, people, gov):
    gov.down.add("*")
    first = _claims((await _verify(client, people["sunita"], ["INCOME"])).json())["INCOME"]
    assert first["status"] == "SOURCE_UNAVAILABLE"

    gov.down.clear()
    second = _claims((await _verify(client, people["sunita"], ["INCOME"])).json())["INCOME"]
    assert second["status"] == "VERIFIED" and second["review_case_id"] is None

    queue = (await client.get("/v1/review/cases?status=PENDING", headers=bearer(people["officer"]))).json()
    assert queue == []
    db.expire_all()
    case = await db.get(ReviewCase, first["review_case_id"])
    assert case.status.value == "RESOLVED_BY_SOURCE" and case.attestation_id == second["attestation_id"]


async def test_reused_case_shows_latest_outcome(client, db, people, gov):
    gov.down.add("*")
    case_id = _claims((await _verify(client, people["sunita"], ["ST_STATUS"])).json())["ST_STATUS"]["review_case_id"]
    gov.down.clear()
    st = _claims((await _verify(client, people["sunita"], ["ST_STATUS"])).json())["ST_STATUS"]
    assert st["review_case_id"] == case_id and st["status"] == "PROVISIONAL"
    db.expire_all()
    case = await db.get(ReviewCase, case_id)
    assert case.reason.value == "IDENTITY_NOT_CONFIRMED" and "Hansdah" in case.explanation
    assert case.attestation_id == st["attestation_id"]


async def test_review_queue_is_scoped_to_the_officers_jurisdiction(client, db, people, gov):
    case_id, _ = await _open_hansdah_case(client, people)
    await make_user(db, "9000000051", UserRole.DISTRICT_OFFICER, "DWO Ranchi", jurisdiction=("Jharkhand", "Ranchi"))
    ranchi = bearer(await login(client, db, "9000000051"))
    assert (await client.get("/v1/review/cases", headers=ranchi)).json() == []
    r = await client.post(f"/v1/review/cases/{case_id}/decision", headers=ranchi,
                          json={"decision": "APPROVE", "notes": "Not my district"})
    assert r.status_code == 404
    assert [c["id"] for c in (await client.get("/v1/review/cases", headers=bearer(people["officer"]))).json()] == [case_id]
