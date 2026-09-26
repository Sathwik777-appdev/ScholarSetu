from app.shared.types import ClaimType, ConsentArtefact, VerificationStatus
from app.verification.identity_resolver import IdentityRecord
from app.verification.plugins.base import SubjectRef, VerificationResult, not_confirmed, parse_date
from app.verification.sources import SourceClient, evidence_hash


class APAARVerifier:
    claim_types = (ClaimType.ACADEMIC_RECORDS,)
    source_name = "APAAR"
    priority = 2

    async def verify(self, claim_type: ClaimType, subject: SubjectRef, consent: ConsentArtefact,
                     client: SourceClient) -> VerificationResult:
        if not subject.apaar_id:
            return not_confirmed(self.source_name, "No APAAR ID on the student record")
        body = await client.request("GET", f"/apaar/students/{subject.apaar_id}/records")
        if body is None:
            return not_confirmed(self.source_name, "APAAR has no academic records for this ID")
        records = body.get("records", [])
        if not records:
            return not_confirmed(self.source_name, "APAAR returned no academic records", body)
        return VerificationResult(
            status=VerificationStatus.VERIFIED, source=self.source_name, confidence=0.9,
            evidence_hash=evidence_hash(body), source_ref=subject.apaar_id, claim_value={"records": records},
            subject_record=IdentityRecord("APAAR", body["name"], parse_date(body.get("dob")), body.get("gender"),
                                          None, None, None),
            reasons=[f"{len(records)} academic record(s) found in APAAR"],
        )
