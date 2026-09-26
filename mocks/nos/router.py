from fastapi import APIRouter
from synthetic_data import db, get_student

router = APIRouter()

@router.get("/applications/{student_ref}")
def get_nos_applications(student_ref: str):
    student = get_student(student_ref)
    if not student:
        return {"applications": []}
    return {
        "applications": [
            {
                "app_id": f"NOS-{student['id']}",
                "country": "UK",
                "university": "Oxford",
                "status": "SELECTED"
            }
        ]
    }

@router.get("/applications/{app_id}/status")
def get_nos_app_status(app_id: str):
    return {"app_id": app_id, "status": "SELECTED", "remarks": "Visa pending"}
