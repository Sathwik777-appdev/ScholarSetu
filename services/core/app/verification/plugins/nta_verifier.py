from datetime import date

from app.shared.types import ClaimType, ConsentArtefact, VerificationStatus
from app.verification.identity_resolver import IdentityRecord
from app.verification.plugins.base import SubjectRef, VerificationResult, not_confirmed, parse_date
from app.verification.sources import SourceClient, evidence_hash


class NTAVerifier:
    claim_types = (ClaimType.NET_JRF,)
    source_name = "UGC-NTA"
    priority = 1

    async def verify(self, claim_type: ClaimType, subject: SubjectRef, consent: ConsentArtefact,
                     client: SourceClient) -> VerificationResult:
        if not subject.nta_roll_number:
            return not_confirmed(self.source_name, "No UGC-NET roll number on the student record")
        body = await client.request("GET", f"/nta/results/{subject.nta_roll_number}")
        if body is None:
            return not_confirmed(self.source_name, "No UGC-NET result for this roll number")
        if body.get("qualification") not in ("JRF", "NET"):
            return not_confirmed(self.source_name, f"Result shows qualification {body.get('qualification')}", body)
        valid_until = parse_date(body.get("valid_until"))
        if valid_until and valid_until < date.today():
            return not_confirmed(self.source_name, f"{body['qualification']} validity ended on {valid_until}", body)
        return VerificationResult(
            status=VerificationStatus.VERIFIED, source=self.source_name, confidence=0.98,
            evidence_hash=evidence_hash(body), source_ref=subject.nta_roll_number,
            claim_value={"qualification": body["qualification"], "subject": body["subject"],
                         "exam_cycle": body["exam_cycle"], "valid_until": body.get("valid_until")},
            subject_record=IdentityRecord("UGC-NTA", body["candidate_name"], parse_date(body.get("dob")),
                                          body.get("gender"), body.get("father_name"), None, None),
            reasons=[f"UGC-NET {body['qualification']} in {body['subject']} ({body['exam_cycle']})"],
        )
