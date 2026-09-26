from fastapi import APIRouter
import uuid

router = APIRouter()

@router.post("/dbt/verify-account")
def verify_account(payload: dict):
    return {
        "status": "SUCCESS",
        "aadhaar_seeded": True,
        "account_status": "ACTIVE",
        "name_match_score": 95
    }

@router.post("/dbt/initiate-payment")
def initiate_payment(payload: dict):
    return {"txn_ref": f"PFMS-{uuid.uuid4()}", "status": "PENDING"}

@router.get("/dbt/status/{txn_ref}")
def get_payment_status(txn_ref: str):
    return {"txn_ref": txn_ref, "status": "SUCCESS", "failure_code": None}

@router.get("/npci/mapper/{aadhaar_ref}")
def npci_mapper(aadhaar_ref: str):
    return {"aadhaar_ref": aadhaar_ref, "seeded": True, "bank_name": "State Bank of India"}
