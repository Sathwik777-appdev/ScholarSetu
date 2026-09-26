from fastapi import APIRouter, HTTPException

from synthetic_data import full_name, get_student

router = APIRouter()


@router.get("/enrolments/{apaar_id}")
def get_enrolment(apaar_id: str):
    """Higher-education enrolment for an APAAR ID. 404 when unknown."""
    student = get_student(apaar_id)
    if not student or "aishe" not in student["sources"]:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return {"apaar_id": apaar_id, "student_name": full_name(student), "dob": student["dob"],
            "gender": student["gender"], "district": student["district"], **student["sources"]["aishe"]}
