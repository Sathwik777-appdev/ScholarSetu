"""Phase 6 (S6, C3, M1): rules as code with JSON-Logic, real facts, one scheme at a time, pathway."""

import json
import re
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.attestation.keys import get_signer
from app.attestation.service import AttestationService
from app.eligibility.models import EligibilityDecision, RuleVersion
from app.eligibility.service import EligibilityService, current_academic_year, load_rule_files
from app.ledger.models import Application, OutboxMessage
from app.ledger.service import LedgerService
from app.shared.types import CanonicalState, ClaimType, SchemeType, VerificationMethod

REPO = Path(__file__).resolve().parents[2]


def test_no_eval_anywhere():
    offenders = []
    for path in list((REPO / "services").rglob("*.py")) + list((REPO / "scripts").rglob("*.py")) + list((REPO / "mocks").rglob("*.py")):
        if re.search(r"(?<![\w.])eval\(", path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(REPO)))
    assert offenders == []


def test_every_parameter_is_sourced_and_unverified():
    for path in (REPO / "rules").glob("*.json"):
        table = json.loads(path.read_text())
        for section in ("parameters", "amounts"):
            for name, param in table.get(section, {}).items():
                assert {"value", "source", "source_url", "verified_by_team"} <= set(param), (path.name, name)
                assert param["verified_by_team"] is False
                assert param["source_url"].startswith("https://")


async def test_rule_files_are_loaded_and_immutable(db, tmp_path):
    versions = (await db.execute(select(RuleVersion))).scalars().all()
    assert {v.scheme for v in versions} == set(SchemeType)
    changed = json.loads((REPO / "rules" / "pre_matric_2026_v1.json").read_text())
    changed["parameters"]["income_ceiling"]["value"] = 1  # same version, different content
    (tmp_path / "pre_matric_2026_v1.json").write_text(json.dumps(changed))
    with pytest.raises(RuntimeError, match="kept version"):
        await load_rule_files(db, str(tmp_path))


async def _attest(db, student_id, claim, value):
    await AttestationService(db, get_signer()).issue_attestation(student_id, claim, value, "test-source",
                                                                 VerificationMethod.API, 0.99, None)
    await db.commit()


async def _verify(client, headers, app_id, claims):
    from tests.conftest import grant_consent
    consent_id = await grant_consent(client, headers, claims)
    r = await client.post("/v1/verify/claims", headers=headers,
                          json={"application_id": app_id, "required_claims": claims, "consent_id": consent_id})
    assert r.status_code == 200, r.text
    return r.json()


async def _check(client, headers, scheme):
    r = await client.post("/v1/eligibility/check", headers=headers, json={"scheme": scheme})
    assert r.status_code == 200, r.text
    return r.json()


async def test_missing_facts_say_what_is_needed(client, users):
    result = await _check(client, await users.headers("rahul"), "PRE_MATRIC")
    assert result["status"] == "NEEDS_INFORMATION" and result["eligible"] is False
    assert set(result["missing"]) >= {"ST_STATUS", "INCOME", "SCHOOL_ENROLMENT"}
    assert any(r["outcome"] == "NEEDS" and "needs INCOME" in r["detail"] for r in result["rules"])


async def test_rahul_is_eligible_for_pre_matric_after_verification(client, demo, users, gov):
    rahul = await users.headers("rahul")
    report = await _verify(client, rahul, demo["rahul_application"], ["IDENTITY", "ST_STATUS", "INCOME", "SCHOOL_ENROLMENT"])
    assert report["overall_status"] == "VERIFIED", report
    result = await _check(client, rahul, "PRE_MATRIC")
    assert result["status"] == "ELIGIBLE", result
    assert result["rule_version"] == "2026-v1"
    # Class 10 is not Post-Matric: the class rule fails, it is not "needs".
    post = await _check(client, rahul, "POST_MATRIC")
    assert post["status"] == "NOT_ELIGIBLE" and any("Class 11" in r for r in post["reasons"])


async def test_sunita_is_eligible_for_post_matric_once_the_st_case_is_approved(client, demo, users, gov):
    sunita = await users.headers("sunita")
    report = await _verify(client, sunita, demo["sunita_application"],
                           ["IDENTITY", "ST_STATUS", "INCOME", "HIGHER_ED", "ACADEMIC_RECORDS"])
    claims = {c["claim_type"]: c["status"] for c in report["claims"]}
    assert claims == {"IDENTITY": "VERIFIED", "ST_STATUS": "PROVISIONAL", "INCOME": "VERIFIED",
                      "HIGHER_ED": "VERIFIED", "ACADEMIC_RECORDS": "VERIFIED"}
    before = await _check(client, sunita, "POST_MATRIC")
    assert before["status"] == "NEEDS_INFORMATION" and before["missing"] == ["ST_STATUS"]

    case_id = next(c["review_case_id"] for c in report["claims"] if c["claim_type"] == "ST_STATUS")
    r = await client.post(f"/v1/review/cases/{case_id}/decision", headers=await users.headers("district"),
                          json={"decision": "APPROVE", "notes": "Hansdah is a spelling of Hansda"})
    assert r.status_code == 200
    after = await _check(client, sunita, "POST_MATRIC")
    assert after["status"] == "ELIGIBLE", after


async def test_income_above_ceiling_is_not_eligible(client, db, demo, users):
    for claim, value in ((ClaimType.ST_STATUS, {"tribe": "Santal"}), (ClaimType.INCOME, {"annual_income": 900000}),
                         (ClaimType.SCHOOL_ENROLMENT, {"class": "10"})):
        await _attest(db, "stu-rahul-002", claim, value)
    result = await _check(client, await users.headers("rahul"), "PRE_MATRIC")
    assert result["status"] == "NOT_ELIGIBLE" and "Family annual income exceeds the scheme ceiling." in result["reasons"]


async def test_every_decision_records_its_rule_version(client, db, users):
    await _check(client, await users.headers("rahul"), "PRE_MATRIC")
    await _check(client, await users.headers("sunita"), "NOS")
    db.expire_all()
    decisions = (await db.execute(select(EligibilityDecision))).scalars().all()
    assert len(decisions) == 2 and all(d.rule_version_id for d in decisions)
    ids = {d.rule_version_id for d in decisions}
    assert await db.scalar(select(func.count()).select_from(RuleVersion).where(RuleVersion.id.in_(ids))) == 2


# ── one scheme at a time ─────────────────────────────────────────────────────


async def _sanction_sunita(db, app_id):
    ledger = LedgerService(db)
    app = await db.get(Application, app_id)
    await ledger.sanction(app, [("Maintenance allowance", Decimal("5000"))], "system:test")
    await db.commit()


async def test_holding_post_matric_and_applying_for_nfst_gives_the_conflict_message(client, db, demo, users):
    await _sanction_sunita(db, demo["sunita_application"])  # Sunita now holds Post-Matric 2026-27
    sunita = await users.headers("sunita")
    year = current_academic_year()
    r = await client.post("/v1/applications", headers=sunita, json={"scheme": "NFST", "academic_year": year})
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["code"] == "ONE_SCHEME_RULE" and detail["can_acknowledge"] is True
    assert detail["message"] == (f"You currently hold Post-Matric for {year}. You can apply for NFST, but you must "
                                 "surrender Post-Matric once NFST is sanctioned.")

    r = await client.post("/v1/applications", headers=sunita,
                          json={"scheme": "NFST", "academic_year": year, "acknowledge_one_scheme_rule": True})
    assert r.status_code == 201
    assert r.json()["provisional_flags"] == [f"MUST_SURRENDER:{demo['sunita_application']}"]


async def test_duplicate_application_for_the_same_scheme_is_refused(client, demo, users):
    r = await client.post("/v1/applications", headers=await users.headers("sunita"),
                          json={"scheme": "POST_MATRIC", "academic_year": "2026-27", "acknowledge_one_scheme_rule": True})
    assert r.status_code == 409 and r.json()["detail"]["can_acknowledge"] is False


async def test_one_scheme_rule_blocks_eligibility_for_another_scheme(client, db, demo, users):
    await _sanction_sunita(db, demo["sunita_application"])
    result = await _check(client, await users.headers("sunita"), "NFST")
    assert any(r["rule_id"] == "nfst_one_scheme" and r["outcome"] == "FAIL" for r in result["rules"])


# ── pathway ───────────────────────────────────────────────────────────────────


async def test_pathway_reflects_the_current_holding(client, demo, users):
    pathway = (await client.get("/v1/me/pathway", headers=await users.headers("sunita"))).json()
    assert pathway["current_scheme"] == "POST_MATRIC" and pathway["current_application_id"] == demo["sunita_application"]
    assert pathway["ladder"][pathway["ladder_position"]] == "POST_MATRIC"


async def test_verified_research_facts_prepare_an_nfst_draft(client, db, demo, users):
    await _attest(db, "stu-sunita-001", ClaimType.NET_JRF, {"qualification": "JRF", "subject": "Anthropology"})
    await _attest(db, "stu-sunita-001", ClaimType.HIGHER_ED, {"course": "PhD Anthropology", "institution": "Ranchi University"})
    draft = await EligibilityService(db).detect_transition("stu-sunita-001", "system:test")
    assert draft is not None and draft.scheme == SchemeType.NFST and draft.canonical_state == CanonicalState.DRAFT
    assert draft.details["institution"] == "Ranchi University"
    draft_id = draft.id
    await db.commit()
    pathway = (await client.get("/v1/me/pathway", headers=await users.headers("sunita"))).json()
    assert pathway["next_eligible"] == "NFST" and pathway["prefilled_application_id"] == draft_id
    subjects = (await db.execute(select(OutboxMessage.subject))).scalars().all()
    assert "pathway.transition_detected" in subjects
    assert await EligibilityService(db).detect_transition("stu-sunita-001", "system:test") is None  # only once


async def test_missing_facts_use_plain_names(client, users):
    result = await _check(client, await users.headers("sunita"), "POST_MATRIC")
    assert "CURRENT_CLASS_OR_COURSE" in result["missing"] and "current_stage_known" not in result["missing"]
