from app.shared.types import ClaimType, ConsentArtefact, VerificationStatus
from app.verification.identity_resolver import IdentityRecord
from app.verification.plugins.base import SubjectRef, VerificationResult, not_confirmed, parse_date
from app.verification.sources import SourceClient, evidence_hash


class AISHEVerifier:
    claim_types = (ClaimType.HIGHER_ED,)
    source_name = "AISHE"
    priority = 1

    async def verify(self, claim_type: ClaimType, subject: SubjectRef, consent: ConsentArtefact,
                     client: SourceClient) -> VerificationResult:
        if not subject.apaar_id:
            return not_confirmed(self.source_name, "No APAAR ID on the student record")
        body = await client.request("GET", f"/aishe/enrolments/{subject.apaar_id}")
        if body is None:
            return not_confirmed(self.source_name, "AISHE has no enrolment for this APAAR ID")
        if body.get("status") != "ENROLLED":
            return not_confirmed(self.source_name, f"AISHE enrolment status is {body.get('status')}", body)
        return VerificationResult(
            status=VerificationStatus.VERIFIED, source=self.source_name, confidence=0.95,
            evidence_hash=evidence_hash(body), source_ref=body["aishe_code"],
            claim_value={"aishe_code": body["aishe_code"], "institution": body["institution"],
                         "course": body["course"], "academic_year": body["academic_year"]},
            subject_record=IdentityRecord("AISHE", body["student_name"], parse_date(body.get("dob")),
                                          body.get("gender"), None, None, body.get("district")),
            reasons=[f"Enrolled in {body['course']} at {body['institution']} (AISHE {body['aishe_code']})"],
        )
