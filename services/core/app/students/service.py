from sqlalchemy.ext.asyncio import AsyncSession

from app.students.models import Student


class StudentNotFound(LookupError):
    pass


async def get_student(db: AsyncSession, student_id: str) -> Student:
    student = await db.get(Student, student_id)
    if student is None:
        raise StudentNotFound(f"Student {student_id} not found")
    return student


async def create_student(db: AsyncSession, **fields) -> Student:
    if await db.get(Student, fields["id"]) is not None:
        raise ValueError(f"Student {fields['id']} already exists")
    student = Student(**fields)
    db.add(student)
    await db.flush()
    return student
