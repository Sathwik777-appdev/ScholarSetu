from datetime import date

from app.shared.types import ClaimType, ConsentArtefact, VerificationStatus
from app.verification.identity_resolver import IdentityRecord
from app.verification.plugins.base import SubjectRef, VerificationResult, not_confirmed, parse_date
from app.verification.sources import SourceClient, evidence_hash

_CERT_TYPE = {ClaimType.ST_STATUS: "caste", ClaimType.INCOME: "income", ClaimType.DOMICILE: "domicile"}


class EDistrictVerifier:
    claim_types = (ClaimType.ST_STATUS, ClaimType.INCOME, ClaimType.DOMICILE)
    source_name = "e-District"
    priority = 2

    async def verify(self, claim_type: ClaimType, subject: SubjectRef, consent: ConsentArtefact,
                     client: SourceClient) -> VerificationResult:
        if not subject.aadhaar_ref:
            return not_confirmed(self.source_name, "No Aadhaar reference on the student record")
        cert_type = _CERT_TYPE[claim_type]
        body = await client.request("GET", f"/edistrict/certificates/{cert_type}/{subject.aadhaar_ref}")
        if body is None:
            return not_confirmed(self.source_name, f"e-District has no {cert_type} certificate for this student")
        if body.get("status") != "VALID":
            return not_confirmed(self.source_name, f"{cert_type} certificate status is {body.get('status')}", body)

        valid_until = parse_date(body.get("valid_until"))
        if valid_until and valid_until < date.today():
            return not_confirmed(self.source_name, f"{cert_type} certificate expired on {valid_until}", body)

        if claim_type == ClaimType.ST_STATUS:
            if body.get("category") != "ST":
                return not_confirmed(self.source_name, f"Certificate category is {body.get('category')}, not ST", body)
            value = {"tribe": body["tribe"], "pvtg": bool(body.get("pvtg", False)),
                     "certificate_no": body["certificate_no"]}
        elif claim_type == ClaimType.INCOME:
            value = {"annual_income": body["annual_income"], "financial_year": body["financial_year"],
                     "certificate_no": body["certificate_no"]}
        else:
            value = {"state": body["state"], "certificate_no": body["certificate_no"]}

        return VerificationResult(
            status=VerificationStatus.VERIFIED, source=self.source_name, confidence=0.95,
            evidence_hash=evidence_hash(body), source_ref=body["certificate_no"], claim_value=value,
            subject_record=IdentityRecord(f"e-District {cert_type} certificate", body["holder_name"],
                                          parse_date(body.get("holder_dob")), body.get("gender"),
                                          body.get("father_name"), None, body.get("district")),
            reasons=[f"e-District {cert_type} certificate {body['certificate_no']} is valid"],
        )
