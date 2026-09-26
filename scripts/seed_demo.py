"""Seed demo students and users for the judge-demo storyline (ARCHITECTURE.md §14).

Demo data lives here, not in core service logic. These users are marked is_demo=True:
they may log in with DEMO_OTP only while the API runs with DEMO_MODE=true.

Run from the repo root (host):      python scripts/seed_demo.py
Or inside the core container:       python /scripts/seed_demo.py

Until the Phase 4 Alembic migration exists, this script also creates the live tables
(app.db_tables.LIVE_TABLES).
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

for candidate in (Path(__file__).resolve().parents[1] / "services" / "core", Path("/app")):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break

from sqlalchemy import select  # noqa: E402

from app.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.db_tables import LIVE_TABLES  # noqa: E402
from app.gateway.models import User  # noqa: E402
from app.shared.types import Gender, UserRole  # noqa: E402
from app.students.models import Student  # noqa: E402

DEMO_USERS = [
    # phone, name, role, student_id, household_id
    ("9876543210", "Sunita Hansda", UserRole.STUDENT, "stu-sunita-001", "hh_hansda_001"),
    ("9876543211", "Rahul Hansda", UserRole.STUDENT, "stu-rahul-002", "hh_hansda_001"),
    ("9876543212", "Babulal Hansda", UserRole.GUARDIAN, None, "hh_hansda_001"),
    ("9876543220", "Kavita Tudu (Hostel Warden)", UserRole.MITRA, None, None),
    ("9876543230", "District Welfare Officer, Dumka", UserRole.DISTRICT_OFFICER, None, None),
    ("9876543240", "MoTA Scholarship Division", UserRole.MINISTRY, None, None),
]


# Student master records. Identifiers match the mock government services (mocks/synthetic_data.py).
DEMO_STUDENTS = [
    dict(id="stu-sunita-001", full_name="Sunita Hansda", name_variants=["Sunita Hansda"], dob=date(2008, 4, 12),
         gender=Gender.FEMALE, father_name="Babulal Hansda", mother_name="Marangmai Hansda", tribe="Santal",
         state="Jharkhand", district="Dumka", household_id="hh_hansda_001",
         aadhaar_ref_token="AREF-JH-0004912", apaar_id="APAAR-JH-2026-0812"),
    dict(id="stu-rahul-002", full_name="Rahul Hansda", name_variants=["Rahul Hansda"], dob=date(2010, 8, 15),
         gender=Gender.MALE, father_name="Babulal Hansda", mother_name="Marangmai Hansda", tribe="Santal",
         state="Jharkhand", district="Dumka", household_id="hh_hansda_001",
         aadhaar_ref_token="AREF-JH-0009914", apaar_id="APAAR-JH-2025-4192"),
]


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=LIVE_TABLES))


async def seed_students() -> None:
    async with AsyncSessionLocal() as db:
        for fields in DEMO_STUDENTS:
            student = await db.get(Student, fields["id"]) or Student(id=fields["id"])
            for key, value in fields.items():
                setattr(student, key, value)
            db.add(student)
        await db.commit()


async def seed_users() -> list[User]:
    seeded = []
    async with AsyncSessionLocal() as db:
        for phone, name, role, student_id, household_id in DEMO_USERS:
            user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
            if user is None:
                user = User(phone=phone)
                db.add(user)
            user.name, user.role, user.student_id, user.household_id = name, role, student_id, household_id
            user.is_active, user.is_demo = True, True
            seeded.append(user)
        await db.commit()
    return seeded


async def main() -> None:
    await create_tables()
    await seed_students()
    users = await seed_users()
    await engine.dispose()
    print(f"Seeded {len(DEMO_STUDENTS)} demo students and {len(users)} demo users:")
    for u in users:
        print(f"  {u.phone}  {u.role.value:<17} {u.name}")


if __name__ == "__main__":
    asyncio.run(main())
