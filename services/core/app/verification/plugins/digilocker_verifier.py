from app.shared.types import ClaimType, ConsentArtefact, VerificationStatus
from app.verification.identity_resolver import IdentityRecord
from app.verification.plugins.base import SubjectRef, VerificationResult, not_confirmed, parse_date
from app.verification.sources import SourceClient, evidence_hash

_DOC_TYPE = {ClaimType.ST_STATUS: "CASTE_CERTIFICATE", ClaimType.ACADEMIC_RECORDS: "MARKSHEET_10"}


class DigiLockerVerifier:
    claim_types = (ClaimType.ST_STATUS, ClaimType.ACADEMIC_RECORDS)
    source_name = "DigiLocker"
    priority = 1

    async def verify(self, claim_type: ClaimType, subject: SubjectRef, consent: ConsentArtefact,
                     client: SourceClient) -> VerificationResult:
        if not subject.aadhaar_ref:
            return not_confirmed(self.source_name, "No Aadhaar reference on the student record")
        doc_type = _DOC_TYPE[claim_type]
        body = await client.request("GET", f"/digilocker/issued/{subject.aadhaar_ref}", params={"doc_type": doc_type})
        if body is None:
            return not_confirmed(self.source_name, f"No issued {doc_type} in the student's DigiLocker")
        data = body.get("data", {})
        if claim_type == ClaimType.ST_STATUS:
            if data.get("category") != "ST":
                return not_confirmed(self.source_name, f"Certificate category is {data.get('category')}, not ST", body)
            value = {"tribe": data["tribe"], "pvtg": bool(data.get("pvtg", False)), "certificate_no": body["doc_id"]}
        else:
            value = {"board": data["board"], "exam": data["exam"], "year": data["year"], "result": data["result"]}
        return VerificationResult(
            status=VerificationStatus.VERIFIED, source=self.source_name, confidence=0.98,
            evidence_hash=evidence_hash(body), source_ref=body["doc_id"], claim_value=value,
            subject_record=IdentityRecord(f"DigiLocker {doc_type}", body["holder_name"],
                                          parse_date(body.get("holder_dob")), body.get("gender"),
                                          body.get("father_name"), None, body.get("district")),
            reasons=[f"Issuer-signed {doc_type} {body['doc_id']} found in DigiLocker"],
        )
