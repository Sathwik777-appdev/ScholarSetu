from fastapi import APIRouter, HTTPException

from synthetic_data import full_name, get_student

router = APIRouter()


@router.get("/students/{apaar_id}/records")
def get_apaar_records(apaar_id: str):
    """Academic records for an APAAR ID. 404 when unknown."""
    student = get_student(apaar_id)
    if not student or "apaar" not in student["sources"]:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return {"apaar_id": apaar_id, "name": full_name(student), "dob": student["dob"], "gender": student["gender"],
            "records": student["sources"]["apaar"]}
