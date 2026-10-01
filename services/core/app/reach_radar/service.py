"""Reach Radar (ARCHITECTURE.md §6.8): coverage gaps by privacy-preserving linkage, plus ministry analytics.

UDISE+ (the enrolment data holder) sends only CLK encodings; ScholarSetu encodes its own scholarship
records the same way. Matching never sees the other side's names or dates. Officials get aggregates;
individual outreach lists go only to the student's own school.
"""

from collections import defaultdict
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dbt_guardian.models import DbtHealthCheck
from app.eligibility.service import current_academic_year
from app.ledger.models import Application
from app.ledger.service import LedgerService
from app.reach_radar import pprl
from app.shared.types import CanonicalState, SchemeType
from app.students.models import Student
from app.verification.sources import SourceClient, SourceUnavailable
from app.verification.transliteration import to_latin


class RadarError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _secret() -> bytes:
    if not settings.PPRL_HMAC_KEY:
        raise RadarError(503, "Reach Radar is not configured (PPRL_HMAC_KEY)")
    return settings.PPRL_HMAC_KEY.encode()


def _pct(part: int, whole: int) -> Optional[float]:
    return round(100 * part / whole, 1) if whole else None


def _previous_year(year: str) -> str:
    start = int(year[:4]) - 1
    return f"{start}-{(start + 1) % 100:02d}"


class ReachRadarService:
    def __init__(self, db: AsyncSession, sources: SourceClient):
        self.db = db
        self.sources = sources

    async def _enrolled(self, district: Optional[str]) -> list[dict]:
        try:
            rows = await self.sources.request("GET", "/udise/pprl/encodings",
                                              params={"district": district} if district else None)
        except SourceUnavailable:
            raise RadarError(503, "UDISE+ encodings could not be fetched; try again later")
        return rows or []

    async def _scholarship_side(self, secret: bytes, district: Optional[str]) -> list[tuple[Optional[str], int]]:
        """Students with a live application this academic year, encoded locally."""
        live = select(Application.student_id).where(Application.academic_year == current_academic_year(),
                                                     Application.canonical_state != CanonicalState.REJECTED)
        query = select(Student).where(Student.id.in_(live))
        if district:
            query = query.where(Student.district == district)
        students = (await self.db.execute(query)).scalars().all()
        return [(pprl.apaar_token(secret, s.apaar_id),
                 pprl.encode(secret, to_latin(s.full_name), s.dob.isoformat(), s.district)) for s in students]

    async def linkage(self, district: Optional[str]) -> tuple[list[dict], set[int], dict[str, int]]:
        secret = _secret()
        enrolled = await self._enrolled(district)
        left = [(r["apaar_token"], pprl.from_b64(r["clk"])) for r in enrolled]
        right = await self._scholarship_side(secret, district)
        matches = pprl.link(left, right)
        methods = {"apaar": sum(m.method == "apaar" for m in matches), "clk": sum(m.method == "clk" for m in matches)}
        return enrolled, {m.left for m in matches}, methods

    async def coverage(self, level: str, district: Optional[str]) -> dict:
        enrolled, matched, methods = await self.linkage(district)
        groups: dict[tuple, dict] = defaultdict(lambda: {"enrolled": 0, "with": 0, "pvtg": 0, "pvtg_with": 0})
        for i, r in enumerate(enrolled):
            key = (r["district"], r["block"] if level == "block" else None)
            g = groups[key]
            g["enrolled"] += 1
            g["with"] += i in matched
            if r["pvtg"]:
                g["pvtg"] += 1
                g["pvtg_with"] += i in matched
        rows = [{"district": d, "block": b, "enrolled_st": g["enrolled"], "with_scholarship": g["with"],
                 "coverage_pct": _pct(g["with"], g["enrolled"]) or 0.0, "pvtg_enrolled": g["pvtg"],
                 "pvtg_with_scholarship": g["pvtg_with"], "pvtg_coverage_pct": _pct(g["pvtg_with"], g["pvtg"])}
                for (d, b), g in sorted(groups.items(), key=lambda kv: (kv[1]["with"] / kv[1]["enrolled"]))]
        return {"level": level, "method": "CLK v1 balanced Bloom filters + hashed APAAR, 1:1 greedy linkage",
                "matched_by_apaar": methods["apaar"], "matched_by_clk": methods["clk"], "rows": rows}

    async def outreach(self, udise_code: str, include_students: bool) -> dict:
        enrolled, matched, _ = await self.linkage(None)
        mine = [(i, r) for i, r in enumerate(enrolled) if r["udise_code"] == udise_code]
        unreached = [r for i, r in mine if i not in matched]
        return {"udise_code": udise_code, "school_name": mine[0][1]["school_name"] if mine else None,
                "unreached_count": len(unreached),
                "students": [{"record_ref": r["record_ref"], "class_": r["class"], "pvtg": r["pvtg"]}
                             for r in unreached] if include_students else None}

    async def bottlenecks(self, scope=None) -> list[dict]:
        groups: dict[tuple, list] = defaultdict(list)
        for row in await LedgerService(self.db).sla_monitor(scope):
            groups[(row["district"], row["state_name"], row["state"].value)].append(row)
        return sorted(({"district": d, "state_name": s, "stage": stage, "open_applications": len(rows),
                        "avg_days_in_stage": round(sum(r["days_in_state"] for r in rows) / len(rows), 1),
                        "sla_breaches": sum(r["breached"] for r in rows)} for (d, s, stage), rows in groups.items()),
                      key=lambda r: (-r["sla_breaches"], -r["avg_days_in_stage"]))

    async def dbt_hotspots(self) -> list[dict]:
        checks = (await self.db.execute(select(DbtHealthCheck, Student.state, Student.district)
                                        .join(Student, Student.id == DbtHealthCheck.student_id)
                                        .order_by(DbtHealthCheck.created_at))).all()
        latest: dict[str, tuple] = {}
        for check, state, district in checks:
            latest[check.application_id] = (check, (state, district))  # later checks overwrite earlier ones
        groups: dict[tuple, dict] = defaultdict(lambda: {"checked": 0, "failing": 0, "issues": defaultdict(int)})
        for check, place in latest.values():
            g = groups[place]
            g["checked"] += 1
            if check.status == "FAIL":
                g["failing"] += 1
                for issue in check.issues:
                    g["issues"][issue["code"]] += 1
        return sorted(({"state_name": st, "district": d, "applications_checked": g["checked"], "failing": g["failing"],
                        "failure_rate_pct": _pct(g["failing"], g["checked"]) or 0.0,
                        "issue_counts": dict(g["issues"])} for (st, d), g in groups.items()),
                      key=lambda r: -r["failure_rate_pct"])

    async def transitions(self) -> list[dict]:
        """Of students who held Pre-Matric last year, how many applied for Post-Matric this year."""
        current = current_academic_year()
        previous = _previous_year(current)
        rows = (await self.db.execute(select(Application.student_id, Application.scheme, Application.academic_year,
                                             Student.state, Student.district)
                                      .join(Student, Student.id == Application.student_id))).all()
        cohort: dict[str, set] = defaultdict(set)
        applied: dict[str, set] = defaultdict(set)
        for student_id, scheme, year, state, district in rows:
            if scheme == SchemeType.PRE_MATRIC and year == previous:
                cohort[(state, district)].add(student_id)
            if scheme == SchemeType.POST_MATRIC and year == current:
                applied[(state, district)].add(student_id)
        return [{"state_name": p[0], "district": p[1], "from_scheme": "PRE_MATRIC", "to_scheme": "POST_MATRIC", "previous_year": previous,
                 "current_year": current, "eligible_cohort": len(ids), "applied": len(ids & applied[p]),
                 "conversion_pct": _pct(len(ids & applied[p]), len(ids))} for p, ids in sorted(cohort.items())]
