from app.shared.types import ClaimType, ConsentArtefact, VerificationStatus
from app.verification.identity_resolver import IdentityRecord
from app.verification.plugins.base import SubjectRef, VerificationResult, not_confirmed, parse_date
from app.verification.sources import SourceClient, evidence_hash


class UIDAIeKYCVerifier:
    claim_types = (ClaimType.IDENTITY,)
    source_name = "UIDAI"
    priority = 1

    async def verify(self, claim_type: ClaimType, subject: SubjectRef, consent: ConsentArtefact,
                     client: SourceClient) -> VerificationResult:
        if not subject.aadhaar_ref:
            return not_confirmed(self.source_name, "No Aadhaar reference on the student record")
        body = await client.request("POST", "/uidai/ekyc", json={"aadhaar_ref": subject.aadhaar_ref})
        if body is None:
            return not_confirmed(self.source_name, "UIDAI has no record for this Aadhaar reference")
        return VerificationResult(
            status=VerificationStatus.VERIFIED, source=self.source_name, confidence=1.0,
            evidence_hash=evidence_hash(body), source_ref=body.get("txn_id"),
            claim_value={"name": body["name"], "dob": body["dob"], "gender": body["gender"]},
            subject_record=IdentityRecord("UIDAI", body["name"], parse_date(body.get("dob")), body.get("gender"),
                                          body.get("care_of"), None, body.get("district")),
            reasons=["UIDAI eKYC returned a matching resident record"],
        )
