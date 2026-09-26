import uuid

from fastapi import APIRouter, HTTPException

from synthetic_data import get_student

router = APIRouter()


@router.post("/ekyc")
def ekyc(payload: dict):
    """eKYC by Aadhaar vault reference. 404 when the reference is unknown."""
    student = get_student(payload.get("aadhaar_ref", ""))
    if not student or "uidai" not in student["sources"]:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return {
        "txn_id": f"UIDAI-{uuid.uuid4().hex[:12]}",
        "name": student["sources"]["uidai"]["name"],
        "dob": student["dob"],
        "gender": student["gender"],
        "care_of": student.get("father_name"),
        "district": student["district"],
        "state": student["state"],
    }
