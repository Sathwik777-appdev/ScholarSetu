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


@router.get("/pprl/encodings")
def pprl_encodings(district: str | None = None):
    """UDISE+ as a PPRL data holder: CLK v1 encodings of enrolled ST students. No names or dates leave here."""
    import os
    from fastapi import HTTPException as _HTTPException
    from pprl_clk import apaar_token, encode, to_b64
    from synthetic_data import ENROLLED_ST
    key = os.environ.get("PPRL_HMAC_KEY")
    if not key:
        raise _HTTPException(status_code=503, detail="PPRL_HMAC_KEY not configured")
    secret = key.encode()
    rows = [r for r in ENROLLED_ST if district is None or r["district"].lower() == district.lower()]
    return [{"record_ref": r["record_ref"], "udise_code": r["udise_code"], "school_name": r["school_name"],
             "block": r["block"], "district": r["district"], "class": r["class"], "pvtg": r["pvtg"],
             "apaar_token": apaar_token(secret, r["apaar_id"]),
             "clk": to_b64(encode(secret, r["name"], r["dob"], r["district"]))} for r in rows]


@router.get("/_synthetic/roster")
def synthetic_roster():
    """Mock-only: the raw synthetic roster, used by scripts/seed_demo.py to build a matching synthetic
    scholarship population. A real UDISE+ would never expose this."""
    from synthetic_data import ENROLLED_ST
    return ENROLLED_ST
