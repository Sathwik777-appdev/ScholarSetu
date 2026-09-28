from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import ANALYTICS_ROLES, officer_covers, require_role
from app.gateway.models import User
from app.shared.types import UserRole
from app.verification.sources import SourceClient, get_source_client
from .schemas import BottleneckRow, CoverageReport, DBTHotspotRow, OutreachList, TransitionRow
from .service import RadarError, ReachRadarService

router = APIRouter(prefix="/v1/analytics", tags=["Reach Radar & Ministry Analytics"])


def get_radar(db: AsyncSession = Depends(get_db), sources: SourceClient = Depends(get_source_client)):
    return ReachRadarService(db, sources)


def _http(exc: RadarError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _district_scope(user: User, district: Optional[str]) -> Optional[str]:
    if user.role == UserRole.DISTRICT_OFFICER:
        return user.jurisdiction_district  # district officers only ever see their own district
    return district


@router.get("/coverage", response_model=CoverageReport)
async def coverage(level: str = Query("block", pattern="^(district|block)$"), district: Optional[str] = None,
                   user: User = Depends(require_role(*ANALYTICS_ROLES)), radar: ReachRadarService = Depends(get_radar)):
    """Share of enrolled ST students (UDISE+) who hold a scholarship, found by privacy-preserving linkage."""
    try:
        report = await radar.coverage(level, _district_scope(user, district))
    except RadarError as exc:
        raise _http(exc)
    if user.role == UserRole.STATE_OFFICER:
        # The UDISE+ roster carries districts only: keep the districts known to be in the officer's state.
        from sqlalchemy import select
        from app.shared import places
        from app.students.models import Student
        in_state = {places.key(d) for d in (await radar.db.execute(select(Student.district).where(
            places.sql_key(Student.state) == places.key(user.jurisdiction_state)).distinct())).scalars()}
        in_state |= {places.key(d) for d in (await radar.db.execute(select(User.jurisdiction_district).where(
            places.sql_key(User.jurisdiction_state) == places.key(user.jurisdiction_state),
            User.jurisdiction_district.is_not(None)).distinct())).scalars()}
        report["rows"] = [r for r in report["rows"] if places.key(r["district"]) in in_state]
    return report


@router.get("/bottlenecks", response_model=list[BottleneckRow])
async def bottlenecks(user: User = Depends(require_role(*ANALYTICS_ROLES)), radar: ReachRadarService = Depends(get_radar)):
    """Where open applications wait longest, from the ledger."""
    return [r for r in await radar.bottlenecks() if officer_covers(user, r["state_name"], r["district"])]


@router.get("/dbt-failures", response_model=list[DBTHotspotRow])
async def dbt_failures(user: User = Depends(require_role(*ANALYTICS_ROLES)), radar: ReachRadarService = Depends(get_radar)):
    """Districts where DBT Guardian finds payments would not land (e.g. unseeded Aadhaar), for bank camps."""
    return [r for r in await radar.dbt_hotspots() if officer_covers(user, r["state_name"], r["district"])]


@router.get("/transitions", response_model=list[TransitionRow])
async def transitions(user: User = Depends(require_role(*ANALYTICS_ROLES)), radar: ReachRadarService = Depends(get_radar)):
    """Pre-Matric holders last year who applied for Post-Matric this year."""
    return [r for r in await radar.transitions() if officer_covers(user, r["state_name"], r["district"])]


@router.get("/outreach/{udise_code}", response_model=OutreachList)
async def outreach(udise_code: str,
                   user: User = Depends(require_role(UserRole.INSTITUTE_OFFICER, *ANALYTICS_ROLES)),
                   radar: ReachRadarService = Depends(get_radar)):
    """Unreached enrolled ST students of one school. The school's own nodal officer gets the list of its own
    record references; everyone else gets the count only."""
    own_school = user.role == UserRole.INSTITUTE_OFFICER and user.institution_code == udise_code
    if user.role == UserRole.INSTITUTE_OFFICER and not own_school:
        raise HTTPException(status_code=403, detail="Outreach lists go only to the student's own institution")
    try:
        return await radar.outreach(udise_code, include_students=own_school)
    except RadarError as exc:
        raise _http(exc)
