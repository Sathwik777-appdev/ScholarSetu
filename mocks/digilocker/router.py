from fastapi import APIRouter
from synthetic_data import db, get_student
import uuid

router = APIRouter()

@router.post("/authorize")
def authorize(payload: dict):
    return {"auth_code": "AUTH_12345"}

@router.post("/token")
def token(payload: dict):
    return {"access_token": "TOK_12345", "expires_in": 3600}

@router.get("/documents")
def list_documents():
    return {
        "documents": [
            {"doc_id": "DOC_CASTE", "type": "CASTE_CERTIFICATE"},
            {"doc_id": "DOC_INCOME", "type": "INCOME_CERTIFICATE"}
        ]
    }

@router.get("/documents/{doc_id}")
def get_document(doc_id: str):
    return {"doc_id": doc_id, "signed_uri": f"https://mock.digilocker.gov.in/{doc_id}.pdf"}

@router.get("/documents/{doc_id}/verify")
def verify_document(doc_id: str):
    return {"doc_id": doc_id, "verified": True, "authenticity_score": 100}
