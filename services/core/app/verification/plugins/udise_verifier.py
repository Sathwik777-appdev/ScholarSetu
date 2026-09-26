from app.shared.types import ClaimType, ConsentArtefact, VerificationStatus
from app.verification.identity_resolver import IdentityRecord
from app.verification.plugins.base import SubjectRef, VerificationResult, not_confirmed, parse_date
from app.verification.sources import SourceClient, evidence_hash


class UDISEVerifier:
    claim_types = (ClaimType.SCHOOL_ENROLMENT,)
    source_name = "UDISE+"
    priority = 1

    async def verify(self, claim_type: ClaimType, subject: SubjectRef, consent: ConsentArtefact,
                     client: SourceClient) -> VerificationResult:
        if not subject.apaar_id:
            return not_confirmed(self.source_name, "No APAAR ID on the student record")
        body = await client.request("GET", f"/udise/students/{subject.apaar_id}")
        if body is None:
            return not_confirmed(self.source_name, "UDISE+ has no enrolment for this APAAR ID")
        if body.get("status") != "ACTIVE":
            return not_confirmed(self.source_name, f"UDISE+ enrolment status is {body.get('status')}", body)
        return VerificationResult(
            status=VerificationStatus.VERIFIED, source=self.source_name, confidence=0.95,
            evidence_hash=evidence_hash(body), source_ref=body["udise_code"],
            claim_value={"udise_code": body["udise_code"], "school_name": body["school_name"],
                         "class": body["class"], "academic_year": body["academic_year"]},
            subject_record=IdentityRecord("UDISE+", body["student_name"], parse_date(body.get("dob")),
                                          body.get("gender"), body.get("father_name"), None, body.get("district")),
            reasons=[f"Active enrolment in {body['school_name']} (UDISE {body['udise_code']})"],
        )
