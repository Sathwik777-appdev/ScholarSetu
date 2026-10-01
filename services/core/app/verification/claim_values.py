"""What an officer must enter when approving a claim no source confirmed (VerificationMethod.MANUAL).

The value becomes an attestation that eligibility rules read (e.g. claims.INCOME.annual_income), so it is
checked like a source's answer would be: the fields each claim type needs, with the right types."""

from datetime import date
from typing import Any

from app.shared.types import ClaimType

_TEXT, _NUMBER, _BOOL, _DATE, _CLASS = "text", "number", "yes/no", "date (YYYY-MM-DD)", "class number (1-12)"

REQUIRED: dict[ClaimType, dict[str, str]] = {
    ClaimType.IDENTITY: {"name": _TEXT, "dob": _DATE},
    ClaimType.ST_STATUS: {"tribe": _TEXT, "pvtg": _BOOL},
    ClaimType.INCOME: {"annual_income": _NUMBER, "financial_year": _TEXT},
    ClaimType.DOMICILE: {"state": _TEXT},
    ClaimType.SCHOOL_ENROLMENT: {"school_name": _TEXT, "class": _CLASS},
    ClaimType.HIGHER_ED: {"institution": _TEXT, "course": _TEXT},
    ClaimType.ACADEMIC_RECORDS: {"exam": _TEXT, "result": _TEXT},
    ClaimType.NET_JRF: {"qualification": _TEXT},
    ClaimType.DISABILITY: {"percentage": _NUMBER},
    ClaimType.TOP_CLASS_INSTITUTION: {"institution": _TEXT},
    ClaimType.FOREIGN_ADMISSION: {"institution": _TEXT, "course": _TEXT},
}
RESERVED = {"verified"}  # set by ScholarSetu when an attestation is read, never typed in


def _ok(kind: str, value: Any) -> bool:
    if kind == _TEXT:
        return isinstance(value, str) and bool(value.strip())
    if kind == _NUMBER:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0
    if kind == _BOOL:
        return isinstance(value, bool)
    if kind == _CLASS:
        return str(value).isdigit() and 1 <= int(value) <= 12
    if kind == _DATE:
        try:
            return date.fromisoformat(str(value)) <= date.today()
        except ValueError:
            return False
    return False


def problems(claim_type: ClaimType, value: dict[str, Any]) -> list[str]:
    """Why a manually entered value is not acceptable; empty when it is."""
    found = [f"'{k}' is set by ScholarSetu and cannot be entered" for k in RESERVED & set(value)]
    for field, kind in REQUIRED.get(claim_type, {}).items():
        if field not in value:
            found.append(f"'{field}' is required ({kind})")
        elif not _ok(kind, value[field]):
            found.append(f"'{field}' must be a {kind}")
    if claim_type == ClaimType.DISABILITY and _ok(_NUMBER, value.get("percentage")) and value["percentage"] > 100:
        found.append("'percentage' must be at most 100")
    return found
