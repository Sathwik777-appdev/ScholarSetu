from fastapi import APIRouter

router = APIRouter()

@router.get("/students/{apaar_id}")
def get_apaar_student(apaar_id: str):
    return {
        "apaar_id": apaar_id,
        "status": "ACTIVE",
        "credits": 45
    }

@router.get("/students/{apaar_id}/records")
def get_apaar_records(apaar_id: str):
    return {
        "records": [
            {"year": "2022-2023", "grade": "9", "result": "PASS"},
            {"year": "2023-2024", "grade": "10", "result": "PASS"}
        ]
    }
