from fastapi import APIRouter, HTTPException

from synthetic_data import get_student

router = APIRouter()


@router.get("/issued/{aadhaar_ref}")
def get_issued_document(aadhaar_ref: str, doc_type: str):
    """An issuer-pushed document from the person's DigiLocker. 404 when absent."""
    student = get_student(aadhaar_ref)
    docs = student["sources"].get("digilocker", {}) if student else {}
    if doc_type not in docs:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    doc = docs[doc_type]
    return {"doc_type": doc_type, "holder_dob": student["dob"], "gender": student["gender"],
            "district": student["district"], **doc}
