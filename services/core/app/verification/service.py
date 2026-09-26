"""Verification Mesh: checks claims against government sources and fails closed (ARCHITECTURE.md §6.4).

Per claim:
  1. Reuse an ACTIVE, unexpired attestation if one exists.
  2. Otherwise ask every source that can verify the claim.
  3. A source's confirmation only counts if the holder named by the source is the student
     (Identity Resolver). A confident match gives VERIFIED; an uncertain one gives PROVISIONAL.
  4. If no source confirms: MANUAL_REVIEW, or SOURCE_UNAVAILABLE when every source errored.
     Nothing is ever reported VERIFIED by default.
Anything short of VERIFIED opens a review case (the application keeps moving) and, where a
source did return a value, a PROVISIONAL attestation.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.attestation.keys import get_signer
from app.attestation.models import Attestation
from app.attestation.service import AttestationService
from app.database import get_db
from app.gateway.models import User
from app.gateway.service import record_audit
from app.ledger.service import LedgerService, get_ledger_service
from app.shared.events import emit
from app.shared.ids import new_id
from app.shared.types import (
    AttestationStatus, ClaimType, ConsentArtefact, ReviewCaseStatus, ReviewDecision, ReviewReason,
    SourceSystem, VerificationMethod, VerificationStatus,
)
from app.students.models import Student
from app.students.service import get_student
from app.verification.identity_resolver import IdentityRecord, IndicIdentityResolver
from app.verification.models import ReviewCase
from app.verification.plugins.aishe_verifier import AISHEVerifier
from app.verification.plugins.apaar_verifier import APAARVerifier
from app.verification.plugins.base import SubjectRef, VerificationResult, VerifierPlugin
from app.verification.plugins.digilocker_verifier import DigiLockerVerifier
from app.verification.plugins.edistrict_verifier import EDistrictVerifier
from app.verification.plugins.nta_verifier import NTAVerifier
from app.verification.plugins.udise_verifier import UDISEVerifier
from app.verification.plugins.uidai_verifier import UIDAIeKYCVerifier
from app.verification.schemas import (
    ClaimVerificationResult, ReviewCaseOut, ReviewDecisionResponse, SourceOutcome, VerificationReport,
)
from app.verification.sources import SourceClient, SourceUnavailable, get_source_client

logger = logging.getLogger("scholarsetu.verification")

REVIEW_SLA = timedelta(days=7)
# A newly verified education fact can move the student to the next scheme on the ladder.
EDUCATION_CLAIMS = {ClaimType.SCHOOL_ENROLMENT, ClaimType.HIGHER_ED, ClaimType.ACADEMIC_RECORDS, ClaimType.NET_JRF,
                    ClaimType.TOP_CLASS_INSTITUTION, ClaimType.FOREIGN_ADMISSION}
OPEN_CASE_STATUSES = (ReviewCaseStatus.PENDING, ReviewCaseStatus.INFO_REQUESTED)

# Better outcomes sort first.
_RANK = {VerificationStatus.VERIFIED: 0, VerificationStatus.PROVISIONAL: 1,
         VerificationStatus.MANUAL_REVIEW: 2, VerificationStatus.SOURCE_UNAVAILABLE: 3}


class ReviewCaseError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def default_plugins() -> list[VerifierPlugin]:
    return [UIDAIeKYCVerifier(), DigiLockerVerifier(), EDistrictVerifier(), UDISEVerifier(), AISHEVerifier(),
            APAARVerifier(), NTAVerifier()]


def subject_from_student(student: Student) -> SubjectRef:
    return SubjectRef(
        student_id=student.id, aadhaar_ref=student.aadhaar_ref_token, apaar_id=student.apaar_id,
        nta_roll_number=student.nta_roll_number, name=student.full_name, name_variants=list(student.name_variants),
        dob=student.dob, gender=student.gender.value, father_name=student.father_name,
        mother_name=student.mother_name, district=student.district,
    )


def _record_of(subject: SubjectRef) -> IdentityRecord:
    return IdentityRecord("ScholarSetu student record", subject.name, subject.dob, subject.gender,
                          subject.father_name, subject.mother_name, subject.district)


@dataclass
class ClaimOutcome:
    claim_type: ClaimType
    status: VerificationStatus
    reason: Optional[ReviewReason] = None
    chosen: Optional[VerificationResult] = None
    identity_decision: Optional[str] = None
    identity_score: Optional[float] = None
    explanation: str = ""
    consulted: list[SourceOutcome] = field(default_factory=list)


class VerificationMeshService:
    def __init__(self, db: AsyncSession, sources: SourceClient, ledger: LedgerService,
                 plugins: Optional[list[VerifierPlugin]] = None,
                 identity_resolver: Optional[IndicIdentityResolver] = None):
        self.db = db
        self.sources = sources
        self.ledger = ledger
        self.attestations = AttestationService(db, get_signer())
        self.identity_resolver = identity_resolver or IndicIdentityResolver()
        self.verifiers: dict[ClaimType, list[VerifierPlugin]] = defaultdict(list)
        for plugin in plugins if plugins is not None else default_plugins():
            for claim_type in plugin.claim_types:
                self.verifiers[claim_type].append(plugin)
        for plugins_for_claim in self.verifiers.values():
            plugins_for_claim.sort(key=lambda p: p.priority)

    # ── verification ────────────────────────────────────────

    async def verify_claims(self, student_id: str, application_id: str, required_claims: list[ClaimType],
                            consent: ConsentArtefact) -> VerificationReport:
        student = await get_student(self.db, student_id)  # StudentNotFound -> 404 in the router
        subject = subject_from_student(student)
        reusable = await self.attestations.find_valid_attestations(student_id, required_claims)

        results: list[ClaimVerificationResult] = []
        case_ids: list[str] = []
        for claim_type in dict.fromkeys(required_claims):  # de-duplicate, keep order
            if claim_type in reusable:
                att = reusable[claim_type]
                results.append(ClaimVerificationResult(
                    claim_type=claim_type, status=VerificationStatus.VERIFIED, confidence=att.confidence,
                    source=att.source, evidence_hash=att.evidence_hash, claim_value=att.claim_value,
                    reasons=[f"Reused attestation {att.id} (issued {att.issued_at.date()} via {att.source})"],
                    attestation_id=att.id, attestation_status=att.status.value,
                ))
                continue

            outcome = await self._verify_one(subject, claim_type, consent)
            result = await self._record_outcome(student, application_id, outcome)
            if result.review_case_id:
                case_ids.append(result.review_case_id)
            results.append(result)

        overall = self._overall(results)
        if any(r.status == VerificationStatus.VERIFIED and r.claim_type in EDUCATION_CLAIMS for r in results):
            await self._detect_transition(student_id)
        await self._publish("verification.completed", "VerificationCompleted", application_id, {
            "student_id": student_id, "overall_status": overall.value,
            "claims": {r.claim_type.value: r.status.value for r in results}, "review_case_ids": case_ids,
        })
        await self.db.commit()
        return VerificationReport(student_id=student_id, application_id=application_id, overall_status=overall,
                                  claims=results, requires_manual_review=bool(case_ids), review_case_ids=case_ids)

    async def _verify_one(self, subject: SubjectRef, claim_type: ClaimType, consent: ConsentArtefact) -> ClaimOutcome:
        plugins = self.verifiers.get(claim_type, [])
        if not plugins:
            return ClaimOutcome(claim_type, VerificationStatus.MANUAL_REVIEW, ReviewReason.NO_AUTOMATED_SOURCE,
                                explanation=f"No automated source can verify {claim_type.value}; an officer must check the documents.")

        candidates: list[ClaimOutcome] = []
        consulted: list[SourceOutcome] = []
        for plugin in plugins:
            try:
                result = await plugin.verify(claim_type, subject, consent, self.sources)
            except SourceUnavailable as exc:
                logger.warning("source unavailable claim=%s source=%s: %s", claim_type.value, plugin.source_name, exc)
                result = VerificationResult(status=VerificationStatus.SOURCE_UNAVAILABLE, source=plugin.source_name,
                                            reasons=[f"{plugin.source_name} could not be reached"])
            consulted.append(SourceOutcome(source=result.source, status=result.status, source_ref=result.source_ref,
                                           evidence_hash=result.evidence_hash, reasons=result.reasons))
            if result.status == VerificationStatus.VERIFIED:
                candidates.append(self._check_identity(subject, claim_type, result))

        if candidates:
            best = min(candidates, key=lambda c: (_RANK[c.status], -(c.identity_score or 0)))
            best.consulted = consulted
            return best

        if all(c.status == VerificationStatus.SOURCE_UNAVAILABLE for c in consulted):
            return ClaimOutcome(claim_type, VerificationStatus.SOURCE_UNAVAILABLE, ReviewReason.SOURCE_UNAVAILABLE,
                                explanation=f"Every source for {claim_type.value} was unreachable "
                                            f"({', '.join(c.source for c in consulted)}). Not verified.",
                                consulted=consulted)
        reasons = "; ".join(f"{c.source}: {', '.join(c.reasons) or c.status.value}" for c in consulted)
        return ClaimOutcome(claim_type, VerificationStatus.MANUAL_REVIEW, ReviewReason.NOT_CONFIRMED_BY_SOURCE,
                            explanation=f"No source confirmed {claim_type.value}. {reasons}", consulted=consulted)

    def _check_identity(self, subject: SubjectRef, claim_type: ClaimType, result: VerificationResult) -> ClaimOutcome:
        """A source's confirmation only counts if the holder it names is this student."""
        if result.subject_record is None:
            return ClaimOutcome(claim_type, VerificationStatus.PROVISIONAL, ReviewReason.IDENTITY_NOT_CONFIRMED,
                                chosen=result,
                                explanation=f"{result.source} confirmed {claim_type.value} but did not say who the holder is.")
        resolution = self.identity_resolver.resolve([_record_of(subject), result.subject_record])
        if resolution.decision == "AUTO_VERIFY":
            status, reason = VerificationStatus.VERIFIED, None
        elif resolution.decision == "PROVISIONAL":
            status, reason = VerificationStatus.PROVISIONAL, ReviewReason.IDENTITY_NOT_CONFIRMED
        else:
            status, reason = VerificationStatus.MANUAL_REVIEW, ReviewReason.IDENTITY_NOT_CONFIRMED
        explanation = (f"{result.source} confirmed {claim_type.value} ({', '.join(result.reasons)}). "
                       f"Holder on the source: '{result.subject_record.name}'; student record: '{subject.name}'. "
                       f"Identity check: {resolution.decision} (score {resolution.overall_score:.2f}). "
                       f"{resolution.explanation}")
        return ClaimOutcome(claim_type, status, reason, chosen=result, identity_decision=resolution.decision,
                            identity_score=round(resolution.overall_score, 4), explanation=explanation)

    async def _record_outcome(self, student: Student, application_id: str, o: ClaimOutcome) -> ClaimVerificationResult:
        chosen = o.chosen
        attestation: Optional[Attestation] = None
        case: Optional[ReviewCase] = None

        if o.status == VerificationStatus.VERIFIED:
            attestation = await self.attestations.issue_attestation(
                student.id, o.claim_type, chosen.claim_value, chosen.source, chosen.method,
                min(chosen.confidence, o.identity_score or chosen.confidence), chosen.evidence_hash)
            await self._resolve_open_case(student.id, application_id, o, attestation)
        else:
            case = await self._open_case(student.id, application_id, o)
            if chosen is not None and chosen.claim_value is not None and case.attestation_id is None:
                attestation = await self.attestations.issue_attestation(
                    student.id, o.claim_type, chosen.claim_value, chosen.source, chosen.method,
                    min(chosen.confidence, o.identity_score or 0.0), chosen.evidence_hash,
                    status=AttestationStatus.PROVISIONAL)
                case.attestation_id = attestation.id
            elif case.attestation_id:
                attestation = await self.attestations.get(case.attestation_id)

        return ClaimVerificationResult(
            claim_type=o.claim_type, status=o.status,
            confidence=attestation.confidence if attestation else 0.0,
            source=chosen.source if chosen else None,
            evidence_hash=chosen.evidence_hash if chosen else None,
            claim_value=chosen.claim_value if chosen else None,
            reasons=[o.explanation] if o.explanation else (chosen.reasons if chosen else []),
            identity_decision=o.identity_decision, identity_score=o.identity_score,
            attestation_id=attestation.id if attestation else None,
            attestation_status=attestation.status.value if attestation else None,
            review_case_id=case.id if case else None,
            sources_consulted=o.consulted,
        )

    async def _find_open_case(self, student_id: str, application_id: str, claim_type: ClaimType) -> Optional[ReviewCase]:
        return (await self.db.execute(
            select(ReviewCase).where(ReviewCase.student_id == student_id, ReviewCase.application_id == application_id,
                                     ReviewCase.claim_type == claim_type, ReviewCase.status.in_(OPEN_CASE_STATUSES))
        )).scalar_one_or_none()

    async def _resolve_open_case(self, student_id: str, application_id: str, o: ClaimOutcome,
                                 attestation: Attestation) -> None:
        """A claim that now verifies automatically no longer needs an officer: close its open case."""
        case = await self._find_open_case(student_id, application_id, o.claim_type)
        if case is None:
            return
        if case.attestation_id and case.attestation_id != attestation.id:
            stale = await self.attestations.get(case.attestation_id)
            if stale is not None and stale.status == AttestationStatus.PROVISIONAL:
                await self.attestations.set_status(stale, AttestationStatus.REVOKED)  # superseded
        case.status = ReviewCaseStatus.RESOLVED_BY_SOURCE
        case.attestation_id = attestation.id
        case.decided_at = datetime.now(timezone.utc)
        case.notes = f"Resolved automatically: {o.explanation}"
        await record_audit(self.db, "REVIEW_CASE_RESOLVED_BY_SOURCE", student_id=student_id,
                           details={"review_case_id": case.id, "attestation_id": attestation.id})

    async def _open_case(self, student_id: str, application_id: str, o: ClaimOutcome) -> ReviewCase:
        """Open a review case, or refresh the one already open for this student/application/claim."""
        existing = await self._find_open_case(student_id, application_id, o.claim_type)
        if existing is not None:
            # Keep the officer's view current: latest outcome, reason, explanation and evidence.
            existing.verification_status = o.status
            existing.reason = o.reason
            existing.explanation = o.explanation
            existing.identity_score = o.identity_score
            existing.evidence_refs = [c.model_dump(mode="json") for c in o.consulted]
            return existing
        now = datetime.now(timezone.utc)
        case = ReviewCase(
            id=new_id(), student_id=student_id, application_id=application_id, claim_type=o.claim_type,
            verification_status=o.status, reason=o.reason, explanation=o.explanation, identity_score=o.identity_score,
            evidence_refs=[c.model_dump(mode="json") for c in o.consulted],
            status=ReviewCaseStatus.PENDING, sla_deadline=now + REVIEW_SLA, created_at=now,
        )
        self.db.add(case)
        await self.db.flush()
        await self._publish("verification.review_required", "ReviewCaseOpened", application_id, {
            "student_id": student_id, "review_case_id": case.id, "claim_type": o.claim_type.value,
            "verification_status": o.status.value, "reason": o.reason.value,
        })
        return case

    @staticmethod
    def _overall(results: list[ClaimVerificationResult]) -> VerificationStatus:
        statuses = [r.status for r in results]
        if all(s == VerificationStatus.VERIFIED for s in statuses):
            return VerificationStatus.VERIFIED
        unverified = [s for s in statuses if s != VerificationStatus.VERIFIED]
        if all(s == VerificationStatus.SOURCE_UNAVAILABLE for s in unverified):
            return VerificationStatus.SOURCE_UNAVAILABLE
        if any(s in (VerificationStatus.MANUAL_REVIEW, VerificationStatus.SOURCE_UNAVAILABLE) for s in unverified):
            return VerificationStatus.MANUAL_REVIEW
        return VerificationStatus.PROVISIONAL

    async def _detect_transition(self, student_id: str) -> None:
        from app.eligibility.service import EligibilityError, EligibilityService
        try:
            await EligibilityService(self.db).detect_transition(student_id, "system:pathway")
        except EligibilityError as exc:  # e.g. rules not loaded: verification itself still stands
            logger.warning("pathway check skipped for %s: %s", student_id, exc.detail)

    async def _publish(self, subject: str, event_type: str, application_id: str, payload: dict) -> None:
        """Queue in the outbox with the rest of the transaction; published to NATS after commit."""
        await emit(self.db, subject, event_type, payload, correlation_id=application_id)

    # ── officer review ──────────────────────────────────────

    async def list_cases(self, status: Optional[ReviewCaseStatus]) -> list[ReviewCaseOut]:
        query = select(ReviewCase, Student.full_name).join(Student, Student.id == ReviewCase.student_id)
        if status is not None:
            query = query.where(ReviewCase.status == status)
        query = query.order_by(ReviewCase.sla_deadline, ReviewCase.created_at)
        return [self._case_out(case, name) for case, name in (await self.db.execute(query)).all()]

    async def decide(self, case_id: str, decision: ReviewDecision, notes: str, officer: User,
                     claim_value: Optional[dict] = None) -> ReviewDecisionResponse:
        case = await self.db.get(ReviewCase, case_id, with_for_update=True)
        if case is None:
            raise ReviewCaseError(404, "Review case not found")
        if case.status not in OPEN_CASE_STATUSES:
            raise ReviewCaseError(409, f"Case already decided ({case.status.value})")
        application = await self.ledger.get_application(case.application_id)
        if application is None:
            raise ReviewCaseError(409, f"Application {case.application_id} is not in the ledger")

        attestation = await self.attestations.get(case.attestation_id) if case.attestation_id else None
        if decision == ReviewDecision.APPROVE:
            if attestation is not None:
                await self.attestations.set_status(attestation, AttestationStatus.ACTIVE)
            else:
                if not claim_value:
                    raise ReviewCaseError(422, "claim_value is required to approve a case with no source evidence")
                attestation = await self.attestations.issue_attestation(
                    case.student_id, case.claim_type, claim_value, source=f"OFFICER:{officer.id}",
                    method=VerificationMethod.MANUAL, confidence=1.0, evidence_hash=None)
                case.attestation_id = attestation.id
            case.status = ReviewCaseStatus.APPROVED
            if case.claim_type in EDUCATION_CLAIMS:
                await self._detect_transition(case.student_id)
        elif decision == ReviewDecision.REJECT:
            if attestation is not None:
                await self.attestations.set_status(attestation, AttestationStatus.REVOKED)
            case.status = ReviewCaseStatus.REJECTED
        else:
            case.status = ReviewCaseStatus.INFO_REQUESTED

        event = await self.ledger.append_event(
            application, "ReviewDecisionRecorded",
            {"review_case_id": case.id, "claim_type": case.claim_type.value, "decision": decision.value,
             "officer_role": officer.role.value, "attestation_id": case.attestation_id,
             "attestation_status": attestation.status.value if attestation else None},
            actor=f"user:{officer.id}:{officer.role.value}", source=SourceSystem.SCHOLARSETU,
        )
        case.decision = decision
        case.decided_by = officer.id
        case.decided_at = datetime.now(timezone.utc)
        case.notes = notes
        case.decision_event_id = event.event_id
        await record_audit(self.db, "REVIEW_DECISION", actor=officer, student_id=case.student_id,
                           details={"review_case_id": case.id, "decision": decision.value,
                                    "ledger_event_id": event.event_id})
        await self.db.commit()
        student = await self.db.get(Student, case.student_id)
        return ReviewDecisionResponse(
            case=self._case_out(case, student.full_name if student else None), ledger_event_id=event.event_id,
            attestation_id=attestation.id if attestation else None,
            attestation_status=attestation.status.value if attestation else None,
        )

    @staticmethod
    def _case_out(case: ReviewCase, student_name: Optional[str]) -> ReviewCaseOut:
        return ReviewCaseOut(
            id=case.id, student_id=case.student_id, student_name=student_name, application_id=case.application_id,
            claim_type=case.claim_type, verification_status=case.verification_status, reason=case.reason,
            explanation=case.explanation, identity_score=case.identity_score, evidence_refs=case.evidence_refs,
            attestation_id=case.attestation_id, status=case.status, decision=case.decision,
            decided_by=case.decided_by, decided_at=case.decided_at, notes=case.notes,
            decision_event_id=case.decision_event_id, sla_deadline=case.sla_deadline, created_at=case.created_at,
        )


def get_verification_service(
    db: AsyncSession = Depends(get_db),
    sources: SourceClient = Depends(get_source_client),
    ledger: LedgerService = Depends(get_ledger_service),
) -> VerificationMeshService:
    return VerificationMeshService(db, sources, ledger)
