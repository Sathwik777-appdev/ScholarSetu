from fastapi import APIRouter

router = APIRouter()

@router.get("/schools/{code}")
def get_school(code: str):
    return {
        "udise_code": code,
        "name": "Eklavya Model Residential School",
        "state": "Jharkhand",
        "district": "Dumka",
        "management": "Ministry of Tribal Affairs"
    }

@router.get("/students/{apaar_id}")
def get_student_enrolment(apaar_id: str):
    return {
        "apaar_id": apaar_id,
        "udise_code": "20140212345",
        "class": "10",
        "section": "A",
        "year": "2023-2024"
    }

@router.get("/verify-enrolment")
def verify_enrolment(apaar_id: str, udise_code: str):
    return {"enrolled": True, "status": "ACTIVE"}
