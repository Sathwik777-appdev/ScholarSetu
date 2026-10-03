"""Seed the demo accounts of a hosted ScholarSetu, through the service layer (ledger hashes and IDs are real).

Only these are created; there is no synthetic population:
  App (sign in with the demo toggle, code 123456):
    Sunita Hansda   student   9876543210   Post-Matric 2026-27 application with the district authority
    Babulal Hansda  guardian  9876543212   Sunita's father (family view)
  Console (sign in with the demo toggle, code 123456; with the toggle off a real code is emailed):
    Institute officer, district officer, state officer and the Ministry, by email.
  Super Admin (Ministry): a real account. It always needs the code emailed to it, demo toggle or not, because it
  can enrol officers.

Demo accounts are is_demo=True: the demo code works for them only when the server has DEMO_MODE=true and the
sign-in came from the demo toggle. Real people sign in with DigiLocker (students) or an emailed code (officers).

    python scripts/seed_demo.py              seed an empty database
    python scripts/seed_demo.py --if-empty   seed only if the demo accounts are not there yet
    python scripts/seed_demo.py --reset      DELETE all people and records (rules and the guideline index are
                                             kept), then seed. Take a database backup first.
"""

import asyncio
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (REPO / "services" / "core", Path("/app")):
    if (candidate / "app").is_dir():
        sys.path.insert(0, str(candidate))
        break

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.database import AsyncSessionLocal, Base, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.attestation.keys import get_signer  # noqa: E402
from app.attestation.service import AttestationService  # noqa: E402
from app.gateway.models import User  # noqa: E402
from app.ledger.models import Household  # noqa: E402
from app.wallet.models import WalletDocument  # noqa: E402
from app.ledger.service import LedgerService  # noqa: E402
from app.shared.types import AttestationStatus, CanonicalState, ClaimType, Gender, SchemeType, UserRole, VerificationMethod  # noqa: E402
from app.students.service import create_student  # noqa: E402

SEED_ACTOR = "system:seed_demo"
REFERENCE_TABLES = {"rule_versions", "guideline_chunks", "alembic_version"}
HOUSEHOLD = dict(id="hh_hansda_001", guardian_name="Babulal Hansda", guardian_phone="9876543212")

# Identifiers match the test government services (mocks/synthetic_data.py).
SUNITA = dict(id="stu-sunita-001", full_name="Sunita Hansda", name_variants=["Sunita Hansda"], dob=date(2008, 4, 12),
              gender=Gender.FEMALE, father_name="Babulal Hansda", mother_name="Marangmai Hansda", tribe="Santal",
              state="Jharkhand", district="Dumka", household_id="hh_hansda_001", preferred_language="hi",
              aadhaar_ref_token="AREF-JH-0004912", apaar_id="APAAR-JH-2026-0812")

# name, role, phone, email, student_id, household_id, (state, district), institution_code, is_demo, digilocker_id
USERS = [
    ("Sunita Hansda", UserRole.STUDENT, "9876543210", None, "stu-sunita-001", "hh_hansda_001", (None, None), None,
     True, "TEST-AREF-JH-0004912"),
    ("Babulal Hansda", UserRole.GUARDIAN, "9876543212", None, None, "hh_hansda_001", (None, None), None, True, None),
    ("Principal, Dumka Government College", UserRole.INSTITUTE_OFFICER, None, "teamace088@gmail.com", None, None,
     ("Jharkhand", "Dumka"), "C-41290", True, None),
    ("District Welfare Officer, Dumka", UserRole.DISTRICT_OFFICER, None, "sathwikjpoojary@gmail.com", None, None,
     ("Jharkhand", "Dumka"), None, True, None),
    ("Tribal Welfare Department, Jharkhand", UserRole.STATE_OFFICER, None, "chethankotian006@gmail.com", None, None,
     ("Jharkhand", None), None, True, None),
    ("MoTA Scholarship Division", UserRole.MINISTRY, "9876543213", "kotianchethan4@gmail.com", None, None, (None, None), None,
     True, None),
    ("Super Admin", UserRole.MINISTRY, None, "sathwikj777@gmail.com", None, None, (None, None), None, False, None),
]


async def reset(db: AsyncSession) -> None:
    names = ", ".join(t.name for t in Base.metadata.sorted_tables if t.name not in REFERENCE_TABLES)
    await db.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    await db.execute(text("ALTER SEQUENCE application_seq RESTART WITH 1"))  # application numbers start again
    await db.commit()


async def seed(db: AsyncSession, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if await db.get(Household, HOUSEHOLD["id"]) is not None:
        raise RuntimeError("Demo data already present; use --reset to start over.")
    db.add(Household(**HOUSEHOLD))
    await db.flush()
    await create_student(db, **SUNITA)
    for name, role, phone, email, student_id, household, (state, district), code, demo, dl_id in USERS:
        db.add(User(name=name, role=role, phone=phone, email=email, student_id=student_id, household_id=household,
                    jurisdiction_state=state, jurisdiction_district=district, institution_code=code,
                    is_active=True, is_demo=demo, digilocker_id=dl_id))
    await db.flush()

    # Sunita: Post-Matric 2026-27 (Class 11), now with the district authority; nothing verified or sanctioned yet.
    ledger = LedgerService(db)
    sunita = await ledger.create_application("stu-sunita-001", SchemeType.POST_MATRIC, "2026-27", SEED_ACTOR,
                                             {"institution": "Dumka Government College", "aishe_code": "C-41290",
                                              "course": "Intermediate (Class 11) Science", "hosteller": False},
                                             occurred_at=now - timedelta(days=20))
    await ledger.transition(sunita, CanonicalState.INSTITUTE_VERIFICATION, SEED_ACTOR, occurred_at=now - timedelta(days=18))
    await ledger.transition(sunita, CanonicalState.AUTHORITY_VERIFICATION, SEED_ACTOR, occurred_at=now - timedelta(days=9))
    # Hardcoded documents for Sunita's wallet
    db.add_all([
        WalletDocument(
            student_id="stu-sunita-001", document_type="INCOME_CERTIFICATE", title="Income Certificate",
            source="DIGILOCKER", source_ref="INC-JH-2026-001", issuer="Revenue Department, Jharkhand",
            storage_key="dummy_income", content_sha256="dummy", mime_type="application/pdf",
            size_bytes=1024, issuer_signed=True, uploaded_by=SEED_ACTOR, created_at=now
        ),
        WalletDocument(
            student_id="stu-sunita-001", document_type="CASTE_CERTIFICATE", title="Caste Certificate",
            source="DIGILOCKER", source_ref="CST-JH-2026-001", issuer="Revenue Department, Jharkhand",
            storage_key="dummy_caste", content_sha256="dummy", mime_type="application/pdf",
            size_bytes=1024, issuer_signed=True, uploaded_by=SEED_ACTOR, created_at=now
        )
    ])
    
    # Hardcoded attestations (passport claims) for Sunita
    att_service = AttestationService(db, get_signer())
    await att_service.issue_attestation(
        student_id="stu-sunita-001", claim_type=ClaimType.IDENTITY,
        claim_value={"name": "Sunita Hansda", "dob": "2008-04-12", "gender": "F"},
        source="UIDAI", method=VerificationMethod.CRYPTOGRAPHIC, confidence=1.0, evidence_hash="dummy"
    )
    await att_service.issue_attestation(
        student_id="stu-sunita-001", claim_type=ClaimType.ST_STATUS,
        claim_value={"tribe": "Santal", "state": "Jharkhand"},
        source="Revenue Department, Jharkhand", method=VerificationMethod.CRYPTOGRAPHIC, confidence=1.0, evidence_hash="dummy"
    )
    await att_service.issue_attestation(
        student_id="stu-sunita-001", claim_type=ClaimType.INCOME,
        claim_value={"family_income": 45000},
        source="Revenue Department, Jharkhand", method=VerificationMethod.CRYPTOGRAPHIC, confidence=1.0, evidence_hash="dummy"
    )
    
    await db.commit()
    return {"sunita_application": sunita.id}


async def main() -> None:
    async with AsyncSessionLocal() as db:
        if "--reset" in sys.argv:
            await reset(db)
            print("All people and records deleted (rules and guideline index kept).")
        elif "--if-empty" in sys.argv and await db.get(Household, HOUSEHOLD["id"]) is not None:
            print("Demo accounts already present; not reseeded.")
            await engine.dispose()
            return
        ids = await seed(db)
    await engine.dispose()
    print("Seeded:", ids)
    for name, role, phone, email, *_rest in USERS:
        demo = _rest[-2]
        print(f"  {(email or phone):<28} {role.value:<18} {name}{'' if demo else '  (real account: emailed code)'}")


if __name__ == "__main__":
    asyncio.run(main())
