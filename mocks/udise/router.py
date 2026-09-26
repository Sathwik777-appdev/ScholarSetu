from fastapi import APIRouter, HTTPException

from synthetic_data import full_name, get_student

router = APIRouter()


@router.get("/students/{apaar_id}")
def get_student_enrolment(apaar_id: str):
    """Latest school enrolment for an APAAR ID. 404 when unknown."""
    student = get_student(apaar_id)
    if not student or "udise" not in student["sources"]:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return {"apaar_id": apaar_id, "student_name": full_name(student), "dob": student["dob"],
            "gender": student["gender"], "father_name": student.get("father_name"),
            "district": student["district"], **student["sources"]["udise"]}
