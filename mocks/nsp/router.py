from fastapi import APIRouter
from synthetic_data import db, get_student

router = APIRouter()

@router.get("/applications/{student_ref}")
def get_nsp_applications(student_ref: str):
    student = get_student(student_ref)
    if not student:
        return {"applications": []}
    return {
        "applications": [
            {
                "app_id": f"NSP-{student['id']}-2023",
                "scheme_name": "Pre-Matric Scholarship for ST",
                "status": "APPROVED",
                "submitted_date": "2023-08-15T10:00:00Z"
            }
        ]
    }

@router.get("/applications/{app_id}/status")
def get_nsp_app_status(app_id: str):
    return {
        "app_id": app_id,
        "status": "APPROVED",
        "verification_level": "STATE_NODAL_OFFICER",
        "remarks": "Verified"
    }

@router.post("/applications/{app_id}/deficiency-response")
def respond_deficiency(app_id: str, payload: dict):
    return {"status": "SUCCESS", "message": "Response accepted"}

@router.get("/applications/{app_id}/payments")
def get_nsp_payments(app_id: str):
    return {
        "payments": [
            {
                "amount": 2500,
                "status": "SUCCESS",
                "date": "2023-11-01T10:00:00Z",
                "txn_ref": "TXN12345"
            }
        ]
    }
