from fastapi import APIRouter

router = APIRouter()

@router.get("/certificates/income/{ref}")
def get_income(ref: str):
    return {"ref": ref, "amount": 120000, "fy": "2023-24", "status": "VALID"}

@router.get("/certificates/caste/{ref}")
def get_caste(ref: str):
    return {"ref": ref, "caste": "Santal", "category": "ST", "status": "VALID"}

@router.get("/certificates/domicile/{ref}")
def get_domicile(ref: str):
    return {"ref": ref, "state": "Jharkhand", "status": "VALID"}

@router.post("/verify")
def verify_cert(payload: dict):
    return {"verified": True, "status": "ACTIVE"}
