from fastapi import APIRouter

router = APIRouter()

@router.get("/institutions/{code}")
def get_institution(code: str):
    return {
        "aishe_code": code,
        "name": "Mock Tribal University",
        "type": "University",
        "state": "Jharkhand",
        "district": "Ranchi"
    }

@router.get("/verify-enrolment")
def verify_enrolment(student_ref: str, aishe_code: str):
    return {"enrolled": True, "course": "B.A. History", "year": 2}
