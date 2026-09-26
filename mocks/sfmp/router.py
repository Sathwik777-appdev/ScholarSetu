from fastapi import APIRouter
from synthetic_data import db, get_student

router = APIRouter()

@router.get("/scholars/{student_ref}")
def get_sfmp_scholar(student_ref: str):
    student = get_student(student_ref)
    if not student:
        return {"error": "Not found"}
    return {
        "scholar_id": f"SFMP-{student['id']}",
        "name": f"{student['first_name']} {student['last_name']}",
        "status": "ACTIVE"
    }

@router.get("/scholars/{student_ref}/fellowship-status")
def get_fellowship_status(student_ref: str):
    return {"status": "AWARDED", "start_date": "2023-01-01", "end_date": "2025-12-31"}

@router.get("/scholars/{student_ref}/payments")
def get_payments(student_ref: str):
    return {"payments": [{"month": "2023-08", "amount": 35000, "status": "DISBURSED"}]}
