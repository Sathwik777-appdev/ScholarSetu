from fastapi import APIRouter, HTTPException

from synthetic_data import get_student

router = APIRouter()


@router.get("/certificates/{cert_type}/{aadhaar_ref}")
def get_certificate(cert_type: str, aadhaar_ref: str):
    """Caste, income or domicile certificate. 404 when the person or certificate is unknown."""
    if cert_type not in ("caste", "income", "domicile"):
        raise HTTPException(status_code=404, detail="UNKNOWN_CERTIFICATE_TYPE")
    student = get_student(aadhaar_ref)
    if not student or cert_type not in student["sources"]:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return dict(student["sources"][cert_type])
