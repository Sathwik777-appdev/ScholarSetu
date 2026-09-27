"""Seed the judge-demo world (ARCHITECTURE.md §14) through the service layer.

Demo data lives here and in the mock services, never in core service logic. Everything is
created with the same code paths the API uses, so ledger hashes, outbox events and IDs are real.

Seeded users are is_demo=True: they may log in with DEMO_OTP only while DEMO_MODE=true.

Run inside the core container:   python /scripts/seed_demo.py
The database must already be migrated (alembic upgrade head). The script refuses to run twice.
"""

import asyncio
import json
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (REPO / "services" / "core", Path("/app")):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break
RULES_DIR = next(p for p in (REPO / "rules", Path("/rules")) if p.is_dir())

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.database import AsyncSessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.gateway.models import User  # noqa: E402
from app.ledger.models import Household  # noqa: E402
from app.ledger.service import LedgerService  # noqa: E402
from app.shared.types import CanonicalState, Gender, PaymentState, SchemeType, UserRole  # noqa: E402
from app.students.service import create_student  # noqa: E402

SEED_ACTOR = "system:seed_demo"
HOUSEHOLD = dict(id="hh_hansda_001", guardian_name="Babulal Hansda", guardian_phone="9876543212")

# Identifiers match the mock government services (mocks/synthetic_data.py).
STUDENTS = [
    dict(id="stu-sunita-001", full_name="Sunita Hansda", name_variants=["Sunita Hansda"], dob=date(2008, 4, 12),
         gender=Gender.FEMALE, father_name="Babulal Hansda", mother_name="Marangmai Hansda", tribe="Santal",
         state="Jharkhand", district="Dumka", household_id="hh_hansda_001", preferred_language="hi",
         aadhaar_ref_token="AREF-JH-0004912", apaar_id="APAAR-JH-2026-0812"),
    dict(id="stu-rahul-002", full_name="Rahul Hansda", name_variants=["Rahul Hansda"], dob=date(2010, 8, 15),
         gender=Gender.MALE, father_name="Babulal Hansda", mother_name="Marangmai Hansda", tribe="Santal",
         state="Jharkhand", district="Dumka", household_id="hh_hansda_001", preferred_language="hi",
         aadhaar_ref_token="AREF-JH-0009914", apaar_id="APAAR-JH-2025-4192"),
    # Salkhan's Post-Matric application lives on NSP; the NSP adapter imports it into the ledger.
    dict(id="stu-salkhan-003", full_name="Salkhan Soren", name_variants=["Salkhan Soren"], dob=date(2007, 12, 1),
         gender=Gender.MALE, father_name="Gopal Soren", mother_name=None, tribe="Santal", state="Jharkhand",
         district="Dumka", household_id=None, preferred_language="hi",
         aadhaar_ref_token="AREF-JH-0005521", apaar_id="APAAR-JH-2026-5521"),
]

USERS = [
    # phone, name, role, student_id, household_id, jurisdiction (state, district)
    ("9876543210", "Sunita Hansda", UserRole.STUDENT, "stu-sunita-001", "hh_hansda_001", (None, None)),
    ("9876543211", "Rahul Hansda", UserRole.STUDENT, "stu-rahul-002", "hh_hansda_001", (None, None)),
    ("9876543213", "Salkhan Soren", UserRole.STUDENT, "stu-salkhan-003", None, (None, None)),
    ("9876543212", "Babulal Hansda", UserRole.GUARDIAN, None, "hh_hansda_001", (None, None)),
    ("9876543220", "Kavita Tudu (Hostel Warden)", UserRole.MITRA, None, None, (None, None)),
    ("9876543225", "Principal, Dumka Government College", UserRole.INSTITUTE_OFFICER, None, None, ("Jharkhand", "Dumka")),
    ("9876543226", "Headmaster, Government High School, Dumka", UserRole.INSTITUTE_OFFICER, None, None, ("Jharkhand", "Dumka")),
    ("9876543230", "District Welfare Officer, Dumka", UserRole.DISTRICT_OFFICER, None, None, ("Jharkhand", "Dumka")),
    ("9876543235", "Tribal Welfare Department, Jharkhand", UserRole.STATE_OFFICER, None, None, ("Jharkhand", None)),
    ("9876543240", "MoTA Scholarship Division", UserRole.MINISTRY, None, None, (None, None)),
]


INSTITUTION_CODES = {"9876543225": "C-41290", "9876543226": "20140212345"}
# Share of each block's enrolled ST students who have registered for a scholarship (synthetic, for Reach Radar).
BLOCK_REGISTRATION_RATE = {"Dumka": 0.8, "Jama": 0.65, "Jarmundi": 0.55, "Kathikund": 0.45, "Shikaripara": 0.3}
FEMALE_NAMES = {"Anita", "Salomi", "Sonamuni", "Phulmani", "Sita", "Rani", "Dulari", "Maino", "Rekha", "Pinky",
                "Parvati", "Sukhmati", "Talamai", "Kiran", "Bahamuni", "Lukhi"}


def _variant(name: str, n: int) -> str:
    """Spellings differ between school and scholarship records; PPRL has to tolerate that."""
    first, last = name.split(" ", 1)
    if n % 3 == 0 and last.endswith("a"):
        return f"{first} {last}h"
    if n % 3 == 1 and "u" in last:
        return f"{first} {last.replace('u', 'oo', 1)}"
    return f"{first[:-1]}{'ee' if first.endswith('i') else first[-1]} {last}"


async def seed_synthetic_population(db: AsyncSession, roster: list[dict], academic_year: str) -> int:
    """Register a (synthetic) share of the UDISE+ roster for scholarships, through the ledger. Returns the count."""
    import hashlib
    ledger = LedgerService(db)
    created = 0
    for n, record in enumerate(roster):
        if record["record_ref"] == "UDISE-REC-000001":  # Rahul is part of the hand-made demo world
            continue
        draw = int(hashlib.sha256(record["record_ref"].encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        if draw >= BLOCK_REGISTRATION_RATE[record["block"]]:
            continue
        name = _variant(record["name"], n) if draw < 0.2 else record["name"]
        student_id = f"stu-syn-{record['record_ref'][-6:]}"
        await create_student(db, id=student_id, full_name=name, name_variants=[name],
                             dob=date.fromisoformat(record["dob"]),
                             gender=Gender.FEMALE if name.split()[0].rstrip("e") in FEMALE_NAMES
                             or record["name"].split()[0] in FEMALE_NAMES else Gender.MALE,
                             father_name=None, mother_name=None, tribe="Santal", pvtg_flag=record["pvtg"],
                             state="Jharkhand", district=record["district"], household_id=None,
                             preferred_language="hi", aadhaar_ref_token=None, apaar_id=record["apaar_id"])
        scheme = SchemeType.PRE_MATRIC if record["class"] <= 10 else SchemeType.POST_MATRIC
        await ledger.create_application(student_id, scheme, academic_year, SEED_ACTOR,
                                        {"school": record["school_name"], "class": record["class"], "synthetic": True})
        created += 1
    await db.commit()
    return created


def scheme_amounts(scheme_file: str) -> dict:
    return json.loads((RULES_DIR / scheme_file).read_text())["amounts"]


async def seed(db: AsyncSession, now: datetime | None = None) -> dict:
    """Create the demo world. Returns the ids the demo and tests refer to."""
    now = now or datetime.now(timezone.utc)
    if await db.get(Household, HOUSEHOLD["id"]) is not None:
        raise RuntimeError("Demo data already present; reset the database to reseed.")
    ledger = LedgerService(db)

    db.add(Household(**HOUSEHOLD))
    await db.flush()
    for fields in STUDENTS:
        await create_student(db, **fields)
    for phone, name, role, student_id, household_id, (j_state, j_district) in USERS:
        db.add(User(phone=phone, name=name, role=role, student_id=student_id, household_id=household_id,
                    jurisdiction_state=j_state, jurisdiction_district=j_district, is_active=True, is_demo=True,
                    institution_code=INSTITUTION_CODES.get(phone)))
    await db.flush()

    # Rahul: Pre-Matric 2025-26, Class 9 hosteller, sanctioned and credited (scene 1: "brother's Pre-Matric credited").
    pre = scheme_amounts("pre_matric_2026_v1.json")
    rahul = await ledger.create_application("stu-rahul-002", SchemeType.PRE_MATRIC, "2025-26", SEED_ACTOR,
                                            {"school": "Government High School, Dumka", "class": 9,
                                             "hosteller": True}, occurred_at=datetime(2025, 8, 1, 10, tzinfo=timezone.utc))
    t = datetime(2025, 8, 10, 10, tzinfo=timezone.utc)
    await ledger.transition(rahul, CanonicalState.INSTITUTE_VERIFICATION, SEED_ACTOR, occurred_at=t)
    await ledger.transition(rahul, CanonicalState.AUTHORITY_VERIFICATION, SEED_ACTOR, occurred_at=t + timedelta(days=12))
    payments = await ledger.sanction(rahul, [("Scholarship (hosteller, Class 9)",
                                              Decimal(pre["hosteller_per_year"]["value"]["class_9"])),
                                             ("Ad-hoc grant", Decimal(pre["adhoc_grant"]["value"]))],
                                     SEED_ACTOR, occurred_at=t + timedelta(days=30))
    for i, p in enumerate(payments):
        await ledger.update_payment(rahul, p.id, PaymentState.INITIATED, SEED_ACTOR, pfms_ref=f"PFMS-JH-2025-{7710 + i}",
                                    occurred_at=t + timedelta(days=45, hours=i))
    for i, p in enumerate(payments):
        await ledger.update_payment(rahul, p.id, PaymentState.CREDITED, SEED_ACTOR,
                                    occurred_at=t + timedelta(days=52, hours=i))

    # Sunita: Post-Matric 2026-27 (Class 11), now with the district authority; nothing sanctioned yet.
    sunita = await ledger.create_application("stu-sunita-001", SchemeType.POST_MATRIC, "2026-27", SEED_ACTOR,
                                             {"institution": "Dumka Government College", "aishe_code": "C-41290",
                                              "course": "Intermediate (Class 11) Science", "hosteller": False},
                                             occurred_at=now - timedelta(days=20))
    await ledger.transition(sunita, CanonicalState.INSTITUTE_VERIFICATION, SEED_ACTOR, occurred_at=now - timedelta(days=18))
    await ledger.transition(sunita, CanonicalState.AUTHORITY_VERIFICATION, SEED_ACTOR, occurred_at=now - timedelta(days=9))

    await db.commit()
    return {"rahul_application": rahul.id, "sunita_application": sunita.id}


async def main() -> None:
    import httpx
    from app.config import settings
    from app.eligibility.service import current_academic_year
    async with AsyncSessionLocal() as db:
        ids = await seed(db)
    async with httpx.AsyncClient(timeout=30) as client:
        roster = (await client.get(f"{settings.MOCK_SERVICE_URL}/udise/_synthetic/roster")).json()
    async with AsyncSessionLocal() as db:
        ids["synthetic_scholarship_registrations"] = await seed_synthetic_population(db, roster, current_academic_year())
    await engine.dispose()
    print("Seeded demo world:")
    for key, value in ids.items():
        print(f"  {key}: {value}")
    print("Demo logins (DEMO_MODE=true only):")
    for phone, name, role, *_ in USERS:
        print(f"  {phone}  {role.value:<17} {name}")


if __name__ == "__main__":
    asyncio.run(main())
