from fastapi import APIRouter

router = APIRouter()

@router.get("/results/{roll_number}")
def get_result(roll_number: str):
    return {
        "roll_number": roll_number,
        "qualified": True,
        "subject": "Sociology",
        "year": "2022",
        "score": 210
    }

@router.get("/verify-qualification")
def verify_nta(roll_number: str):
    return {"verified": True, "qualification": "JRF"}
