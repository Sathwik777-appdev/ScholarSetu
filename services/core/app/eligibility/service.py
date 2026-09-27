"""Eligibility & Pathway Engine (ARCHITECTURE.md §6.5): rules-as-code with JSON-Logic.

Decision tables live only in rules/*.json. They are loaded into rule_versions (immutable per
scheme + version + effective date); every decision records the rule version and the facts used.
Facts come from the student's ACTIVE attestations and ledger holdings. A rule whose input fact is
missing yields "needs <fact>", never a silent false.
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends
from json_logic import jsonLogic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.attestation.models import Attestation
from app.config import settings
from app.database import get_db
from app.eligibility.models import EligibilityDecision, RuleVersion
from app.eligibility.schemas import EligibilityResult, OneSchemeCheck, RuleOutcome, ScholarshipPathway
from app.ledger.models import Application
from app.ledger.service import HOLDING_STATES, LedgerService
from app.shared.events import emit
from app.shared.types import AttestationStatus, CanonicalState, ClaimType, SchemeType
from app.students.models import Student

logger = logging.getLogger("scholarsetu.eligibility")

LADDER = [SchemeType.PRE_MATRIC, SchemeType.POST_MATRIC, SchemeType.TOP_CLASS, SchemeType.NFST, SchemeType.NOS]
SCHEME_LABEL = {SchemeType.PRE_MATRIC: "Pre-Matric", SchemeType.POST_MATRIC: "Post-Matric",
                SchemeType.TOP_CLASS: "Top Class", SchemeType.NFST: "NFST", SchemeType.NOS: "NOS"}
OPEN_STATES = set(CanonicalState) - {CanonicalState.REJECTED, CanonicalState.CREDITED}
_MISSING = object()
# Plain names for non-attestation facts, shown in "needs ..." reasons.
FACT_LABELS = {"current_stage_known": "CURRENT_CLASS_OR_COURSE", "current_class": "CURRENT_CLASS",
               "course_level": "COURSE_LEVEL", "age": "DATE_OF_BIRTH",
               "has_other_active_mota_scholarship": "SCHOLARSHIP_HOLDINGS"}


class EligibilityError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def current_academic_year(today: Optional[date] = None) -> str:
    today = today or date.today()
    start = today.year if today.month >= settings.ACADEMIC_YEAR_START_MONTH else today.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def _lookup(data: dict, path: str) -> Any:
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return _MISSING if node is None else node


def _course_level(text: str) -> Optional[str]:
    t = text.lower()
    if re.search(r"post[\s-]?doc", t):
        return "Post-doctoral"
    if re.search(r"ph\.?\s?d", t):
        return "PhD"
    if re.search(r"m\.?\s?phil", t):
        return "M.Phil"
    if re.search(r"\bmaster|\bm\.?\s?(a|sc|tech|com|ba|s)\b|\bpost[\s-]?graduat", t):
        return "Masters"
    return None


# ── rule files ───────────────────────────────────────────────────────────────


def _read_rule_files(directory: Path) -> list[tuple[Path, bytes]]:
    return [(path, path.read_bytes()) for path in sorted(directory.glob("*.json"))]


async def load_rule_files(db: AsyncSession, rules_dir: Optional[str] = None) -> int:
    """Load rules/*.json into rule_versions. Refuses a changed file that kept the same version."""
    loaded = 0
    files = await asyncio.to_thread(_read_rule_files, Path(rules_dir or settings.RULES_DIR))
    for path, raw in files:
        table = json.loads(raw)
        digest = hashlib.sha256(raw).hexdigest()
        scheme, version = SchemeType(table["scheme"]), table["version"]
        effective = date.fromisoformat(table["effective_from"])
        existing = (await db.execute(select(RuleVersion).where(
            RuleVersion.scheme == scheme, RuleVersion.version == version,
            RuleVersion.effective_from == effective))).scalar_one_or_none()
        if existing is None:
            db.add(RuleVersion(scheme=scheme, version=version, effective_from=effective, content_sha256=digest,
                               decision_table=table))
            loaded += 1
        elif existing.content_sha256 != digest:
            raise RuntimeError(f"{path.name} changed but kept version {version}; publish it as a new version")
    await db.commit()
    return loaded


class EligibilityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ledger = LedgerService(db)

    async def rule_version(self, scheme: SchemeType, on: Optional[date] = None) -> RuleVersion:
        on = on or date.today()
        version = (await self.db.execute(
            select(RuleVersion).where(RuleVersion.scheme == scheme, RuleVersion.effective_from <= on)
            .order_by(RuleVersion.effective_from.desc(), RuleVersion.loaded_at.desc()).limit(1)
        )).scalar_one_or_none()
        if version is None:
            raise EligibilityError(503, f"No rules loaded for {scheme.value}")
        return version

    # ── facts ───────────────────────────────────────────────

    async def active_holdings(self, student_id: str, academic_year: Optional[str] = None) -> list[Application]:
        """Scholarships the student currently holds (any source system), for the one-scheme rule."""
        academic_year = academic_year or current_academic_year()
        return list((await self.db.execute(select(Application).where(
            Application.student_id == student_id, Application.canonical_state.in_(HOLDING_STATES),
            Application.academic_year == academic_year))).scalars())

    async def facts(self, student: Student, scheme: SchemeType) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        attestations = (await self.db.execute(select(Attestation).where(
            Attestation.student_id == student.id, Attestation.status == AttestationStatus.ACTIVE))).scalars()
        claims: dict[str, dict] = {}
        for att in attestations:
            if att.valid_until is not None and (att.valid_until if att.valid_until.tzinfo
                                                else att.valid_until.replace(tzinfo=timezone.utc)) <= now:
                continue
            claims[att.claim_type.value] = {"verified": True, **att.claim_value}
        facts: dict[str, Any] = {"claims": claims}

        current_class = None
        if "SCHOOL_ENROLMENT" in claims and str(claims["SCHOOL_ENROLMENT"].get("class", "")).isdigit():
            current_class = int(claims["SCHOOL_ENROLMENT"]["class"])
        higher = claims.get("HIGHER_ED", {})
        if current_class is None and higher:
            m = re.search(r"class\s*(\d{1,2})", str(higher.get("course", "")), re.I)
            current_class = int(m.group(1)) if m else None
        facts["current_class"] = current_class
        facts["current_stage_known"] = True if (current_class is not None or higher) else None
        level_source = " ".join(str(claims.get(c, {}).get("course", "")) for c in ("HIGHER_ED", "FOREIGN_ADMISSION"))
        facts["course_level"] = _course_level(level_source)
        reference = date(date.today().year, 7, 1)  # schemes measure age on 1 July of the award year
        facts["age"] = reference.year - student.dob.year - ((reference.month, reference.day) < (student.dob.month, student.dob.day))
        holdings = [a for a in await self.active_holdings(student.id) if a.scheme != scheme]
        facts["has_other_active_mota_scholarship"] = bool(holdings)
        facts["holdings"] = [{"application_id": a.id, "scheme": a.scheme.value, "academic_year": a.academic_year}
                             for a in holdings]
        return facts

    # ── evaluation ──────────────────────────────────────────

    async def check_eligibility(self, student_id: str, scheme: SchemeType, record: bool = True) -> EligibilityResult:
        student = await self.db.get(Student, student_id)
        if student is None:
            raise EligibilityError(404, f"Student {student_id} not found")
        version = await self.rule_version(scheme)
        table = version.decision_table
        facts = await self.facts(student, scheme)
        params = {k: v["value"] for k, v in table.get("parameters", {}).items()}
        data = {**facts, "params": params}

        outcomes, reasons, missing = [], [], []
        failed = False
        for rule in table["rules"]:
            absent = [n for n in rule.get("needs", []) if _lookup(data, n) is _MISSING]
            if absent:
                labels = [n.split(".")[1] if n.startswith("claims.") else FACT_LABELS.get(n, n) for n in absent]
                missing.extend(labels)
                outcomes.append(RuleOutcome(rule_id=rule["id"], outcome="NEEDS", detail=f"needs {', '.join(labels)}"))
                continue
            if jsonLogic(rule["logic"], data):
                outcomes.append(RuleOutcome(rule_id=rule["id"], outcome="PASS", detail="satisfied"))
            else:
                failed = True
                reasons.append(rule["failure_reason"])
                outcomes.append(RuleOutcome(rule_id=rule["id"], outcome="FAIL", detail=rule["failure_reason"]))
        if failed:
            status = "NOT_ELIGIBLE"
        elif missing:
            status = "NEEDS_INFORMATION"
            reasons.append("Needs verified " + ", ".join(dict.fromkeys(missing)) + ".")
        else:
            status = "ELIGIBLE"
            reasons.append(f"All {SCHEME_LABEL[scheme]} criteria are met under rules {version.version}.")

        result = EligibilityResult(
            scheme=scheme, status=status, eligible=status == "ELIGIBLE", reasons=reasons,
            missing=list(dict.fromkeys(missing)), rule_version=version.version, rule_version_id=version.id,
            rules=outcomes, required_attestations=[ClaimType(c) for c in table.get("required_attestations", [])],
        )
        if record:
            decision = EligibilityDecision(student_id=student_id, scheme=scheme, rule_version_id=version.id,
                                           status=status, reasons=reasons, missing=result.missing, facts=facts)
            self.db.add(decision)
            await self.db.flush()
            result.decision_id = decision.id
        return result

    # ── one scheme at a time ────────────────────────────────

    async def check_one_scheme_rule(self, student_id: str, target: SchemeType, academic_year: str) -> OneSchemeCheck:
        same = (await self.db.execute(select(Application).where(
            Application.student_id == student_id, Application.scheme == target,
            Application.academic_year == academic_year,
            Application.canonical_state.in_(OPEN_STATES | HOLDING_STATES)))).scalars().first()
        if same is not None:
            return OneSchemeCheck(has_conflict=True, blocking=True, current_holding=target,
                                  holding_application_id=same.id,
                                  message=f"You already have a {SCHEME_LABEL[target]} application for {academic_year} "
                                          f"({same.id}).")
        holdings = [a for a in await self.active_holdings(student_id, academic_year) if a.scheme != target]
        if holdings:
            held = holdings[0]
            return OneSchemeCheck(
                has_conflict=True, blocking=False, current_holding=held.scheme, holding_application_id=held.id,
                message=(f"You currently hold {SCHEME_LABEL[held.scheme]} for {held.academic_year}. You can apply for "
                         f"{SCHEME_LABEL[target]}, but you must surrender {SCHEME_LABEL[held.scheme]} once "
                         f"{SCHEME_LABEL[target]} is sanctioned."))
        return OneSchemeCheck(has_conflict=False, blocking=False, message="No other scholarship is held for this year.")

    # ── pathway ─────────────────────────────────────────────

    def _next_rung(self, facts: dict) -> tuple[Optional[SchemeType], Optional[str], Optional[str]]:
        claims = facts["claims"]
        if "FOREIGN_ADMISSION" in claims:
            return SchemeType.NOS, "POSTGRADUATE_ABROAD", "Foreign university admission verified"
        if "NET_JRF" in claims and facts.get("course_level") in ("PhD", "M.Phil"):
            return SchemeType.NFST, "RESEARCH", "UGC-NET/JRF result and M.Phil/Ph.D registration verified"
        if "TOP_CLASS_INSTITUTION" in claims:
            return SchemeType.TOP_CLASS, "PREMIER_INSTITUTE", "Admission to a notified premier institution verified"
        cls = facts.get("current_class")
        if cls is not None and cls >= 11 or "HIGHER_ED" in claims:
            return SchemeType.POST_MATRIC, "POST_MATRIC", "Class 11 or higher enrolment verified"
        if cls in (9, 10):
            return SchemeType.PRE_MATRIC, "SECONDARY", f"Class {cls} enrolment verified"
        return None, None, None

    async def get_pathway(self, student_id: str) -> ScholarshipPathway:
        student = await self.db.get(Student, student_id)
        if student is None:
            raise EligibilityError(404, f"Student {student_id} not found")
        apps = await self.ledger.applications_for(student_id)
        # The current rung is the latest real application; pre-filled DRAFTs are offers, not holdings.
        current = next((a for a in sorted(apps, key=lambda a: a.created_at, reverse=True)
                        if a.canonical_state not in (CanonicalState.REJECTED, CanonicalState.DRAFT)), None)
        facts = await self.facts(student, current.scheme if current else SchemeType.PRE_MATRIC)
        next_scheme, stage, trigger = self._next_rung(facts)
        year = current_academic_year()
        draft = next((a for a in apps if a.scheme == next_scheme and a.academic_year == year
                      and a.canonical_state == CanonicalState.DRAFT), None)
        return ScholarshipPathway(
            current_scheme=current.scheme if current else None,
            current_state=current.canonical_state if current else None,
            current_application_id=current.id if current else None, ladder=LADDER,
            ladder_position=LADDER.index(current.scheme) if current else None, education_stage=stage,
            next_eligible=next_scheme if (current is None or next_scheme != current.scheme) else None,
            transition_trigger=trigger if (current is None or next_scheme != current.scheme) else None,
            prefilled_application_id=draft.id if draft else None,
        )

    async def detect_transition(self, student_id: str, actor: str) -> Optional[Application]:
        """If verified facts put the student on a new rung, prepare a pre-filled DRAFT and announce it."""
        pathway = await self.get_pathway(student_id)
        target = pathway.next_eligible
        if target is None or pathway.prefilled_application_id:
            return None
        year = current_academic_year()
        if (await self.check_one_scheme_rule(student_id, target, year)).blocking:
            return None
        student = await self.db.get(Student, student_id)
        facts = await self.facts(student, target)
        prefill = {"prefilled_from_attestations": sorted(facts["claims"]),
                   "transition_trigger": pathway.transition_trigger}
        for claim in ("HIGHER_ED", "SCHOOL_ENROLMENT"):
            if claim in facts["claims"]:
                prefill["institution"] = facts["claims"][claim].get("institution") or facts["claims"][claim].get("school_name")
                prefill["course"] = facts["claims"][claim].get("course") or facts["claims"][claim].get("class")
        draft = await self.ledger.create_application(student_id, target, year, actor, prefill,
                                                     initial_state=CanonicalState.DRAFT)
        await emit(self.db, "pathway.transition_detected", "TransitionDetected",
                   {"student_id": student_id, "application_id": draft.id, "scheme": target.value,
                    "trigger": pathway.transition_trigger}, correlation_id=draft.id)
        return draft


def get_eligibility_service(db: AsyncSession = Depends(get_db)) -> EligibilityService:
    return EligibilityService(db)
