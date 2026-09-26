from fastapi import APIRouter, HTTPException

router = APIRouter()

# No demo persona holds a UGC-NET result yet; unknown roll numbers return 404.
RESULTS: dict[str, dict] = {}


@router.get("/results/{roll_number}")
def get_result(roll_number: str):
    if roll_number not in RESULTS:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return RESULTS[roll_number]
