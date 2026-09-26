from sqlalchemy.ext.asyncio import AsyncSession

from app.students.models import Student


class StudentNotFound(LookupError):
    pass


async def get_student(db: AsyncSession, student_id: str) -> Student:
    student = await db.get(Student, student_id)
    if student is None:
        raise StudentNotFound(f"Student {student_id} not found")
    return student
