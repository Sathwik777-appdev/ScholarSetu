"""Phase 7: Reach Radar computes coverage from real linkage over the UDISE+ roster; outreach is scoped."""

import pytest

from app.config import settings
from app.eligibility.service import current_academic_year
from app.ledger.service import LedgerService
from app.shared.types import Gender, SchemeType
from app.students.service import create_student
from tests.demo_world import seed_synthetic_population
from tests.conftest import mocks_data


@pytest.fixture
async def population(db, demo, gov):
    return await seed_synthetic_population(db, mocks_data.ENROLLED_ST, current_academic_year())


async def test_coverage_comes_from_linkage(client, users, population):
    report = (await client.get("/v1/analytics/coverage", headers=await users.headers("ministry"))).json()
    rows = {r["block"]: r for r in report["rows"]}
    assert set(rows) == {"Dumka", "Jama", "Jarmundi", "Kathikund", "Shikaripara"}
    assert sum(r["enrolled_st"] for r in rows.values()) == len(mocks_data.ENROLLED_ST)
    assert sum(r["with_scholarship"] for r in rows.values()) == population  # every registration found, no false links
    assert report["matched_by_clk"] > 0 and report["matched_by_apaar"] > 0
    assert rows["Shikaripara"]["coverage_pct"] < rows["Dumka"]["coverage_pct"]


async def test_coverage_changes_when_the_data_changes(client, db, users, population):
    from datetime import date
    from app.students.models import Student
    ministry = await users.headers("ministry")
    before = (await client.get("/v1/analytics/coverage?level=district", headers=ministry)).json()["rows"][0]
    unreached = None
    for record in mocks_data.ENROLLED_ST:
        if record["record_ref"] != "UDISE-REC-000001" and await db.get(Student, f"stu-syn-{record['record_ref'][-6:]}") is None:
            unreached = record
            break
    await create_student(db, id="stu-new-1", full_name=unreached["name"], name_variants=[],
                         dob=date.fromisoformat(unreached["dob"]), gender=Gender.OTHER, father_name=None,
                         mother_name=None, tribe="Santal", state="Jharkhand", district="Dumka", household_id=None,
                         aadhaar_ref_token=None, apaar_id=None)
    await LedgerService(db).create_application("stu-new-1", SchemeType.PRE_MATRIC, current_academic_year(), "system:test")
    await db.commit()
    after = (await client.get("/v1/analytics/coverage?level=district", headers=ministry)).json()["rows"][0]
    assert after["with_scholarship"] == before["with_scholarship"] + 1
    assert after["coverage_pct"] > before["coverage_pct"]


async def test_outreach_list_only_for_the_schools_own_officer(client, users, population):
    own = await client.get("/v1/analytics/outreach/20140212345", headers=await users.headers("headmaster"))
    assert own.status_code == 200 and own.json()["students"] is not None
    assert own.json()["unreached_count"] == len(own.json()["students"]) > 0
    assert {"record_ref", "class_", "pvtg"} == set(own.json()["students"][0])  # no names or dates
    other = await client.get("/v1/analytics/outreach/20140600411", headers=await users.headers("headmaster"))
    assert other.status_code == 403
    ministry = (await client.get("/v1/analytics/outreach/20140212345", headers=await users.headers("ministry"))).json()
    assert ministry["students"] is None and ministry["unreached_count"] == own.json()["unreached_count"]


async def test_reach_radar_needs_the_linkage_key(client, users, population, monkeypatch):
    monkeypatch.setattr(settings, "PPRL_HMAC_KEY", None)
    assert (await client.get("/v1/analytics/coverage", headers=await users.headers("ministry"))).status_code == 503


async def test_analytics_are_computed_not_fixed(client, users, population):
    ministry = await users.headers("ministry")
    bottlenecks = (await client.get("/v1/analytics/bottlenecks", headers=ministry)).json()
    assert any(b["stage"] == "SUBMITTED" and b["open_applications"] == population for b in bottlenecks)
    transitions = (await client.get("/v1/analytics/transitions", headers=ministry)).json()
    assert transitions and transitions[0]["eligible_cohort"] == 1  # Rahul held Pre-Matric last year
    assert (await client.get("/v1/analytics/dbt-failures", headers=ministry)).json() == []  # no checks run yet
