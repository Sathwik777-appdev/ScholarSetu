from fastapi import APIRouter
from synthetic_data import db, get_student

router = APIRouter()

@router.post("/ekyc")
def ekyc(payload: dict):
    aadhaar = payload.get("aadhaar")
    student = get_student(aadhaar)
    if not student:
        return {"error": "Invalid Aadhaar"}
    
    return {
        "status": "SUCCESS",
        "data": {
            "name": f"{student['first_name']} {student['last_name']}",
            "dob": student['dob'],
            "gender": student['gender'],
            "address": f"{student['district']}, {student['state']}",
            "photo_hash": "mock_hash_12345"
        }
    }

@router.post("/auth/otp")
def auth_otp(payload: dict):
    return {"status": "SUCCESS", "message": "OTP sent"}
