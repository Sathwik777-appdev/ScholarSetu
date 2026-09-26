"""Seed demo users for the judge-demo storyline (ARCHITECTURE.md §14).

Demo data lives here, not in core service logic. These users are marked is_demo=True:
they may log in with DEMO_OTP only while the API runs with DEMO_MODE=true.

Run from the repo root (host):      python scripts/seed_demo.py
Or inside the core container:       python /scripts/seed_demo.py

Phase 1 note: until the Phase 4 Alembic migration exists, this script also creates the
Phase 1 tables (users, otp_challenges, assist_sessions, audit_log, outbound_sms).
"""

import asyncio
import sys
from pathlib import Path

for candidate in (Path(__file__).resolve().parents[1] / "services" / "core", Path("/app")):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break

from sqlalchemy import select  # noqa: E402

from app.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.gateway.models import PHASE1_TABLES, User  # noqa: E402
from app.shared.types import UserRole  # noqa: E402

DEMO_USERS = [
    # phone, name, role, student_id, household_id
    ("9876543210", "Sunita Hansda", UserRole.STUDENT, "stu-sunita-001", "hh_hansda_001"),
    ("9876543211", "Rahul Hansda", UserRole.STUDENT, "stu-rahul-002", "hh_hansda_001"),
    ("9876543212", "Babulal Hansda", UserRole.GUARDIAN, None, "hh_hansda_001"),
    ("9876543220", "Kavita Tudu (Hostel Warden)", UserRole.MITRA, None, None),
    ("9876543230", "District Welfare Officer, Dumka", UserRole.DISTRICT_OFFICER, None, None),
    ("9876543240", "MoTA Scholarship Division", UserRole.MINISTRY, None, None),
]


async def create_phase1_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=PHASE1_TABLES))


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
    await create_phase1_tables()
    users = await seed_users()
    await engine.dispose()
    print(f"Seeded {len(users)} demo users:")
    for u in users:
        print(f"  {u.phone}  {u.role.value:<17} {u.name}")


if __name__ == "__main__":
    asyncio.run(main())
