import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.students.models import Student
from app.attestation.service import AttestationService, get_signer

async def main():
    async with AsyncSessionLocal() as db:
        student = await db.get(Student, "stu-sunita-001")
        print("Student:", student.full_name if student else None)

if __name__ == "__main__":
    asyncio.run(main())
