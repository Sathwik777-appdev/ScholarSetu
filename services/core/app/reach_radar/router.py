from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import ANALYTICS_ROLES, require_role
from .schemas import (
    CoverageAnalysisResult,
    CoverageHeatmapEntry,
    BottleneckEntry,
    DBTFailureHotspot,
    TransitionEntry,
    OutreachList
)
from .service import ReachRadarService

# Ministry, state and district officers only (aggregate analytics and outreach lists).
router = APIRouter(prefix="/v1/analytics", tags=["Reach Radar"],
                   dependencies=[Depends(require_role(*ANALYTICS_ROLES))])

def get_reach_radar_service(db: AsyncSession = Depends(get_db)) -> ReachRadarService:
    return ReachRadarService(db=db)

@router.get("/coverage", response_model=list[CoverageHeatmapEntry])
async def get_coverage_heatmap(
    level: str = Query("district", description="Level of aggregation (state, district, block)"),
    service: ReachRadarService = Depends(get_reach_radar_service)
):
    """Get coverage heatmap data."""
    return await service.get_coverage_heatmap(level)

@router.get("/bottlenecks", response_model=list[BottleneckEntry])
async def get_bottlenecks(
    service: ReachRadarService = Depends(get_reach_radar_service)
):
    """Get stage bottlenecks."""
    return await service.get_bottleneck_analysis()

@router.get("/dbt-failures", response_model=list[DBTFailureHotspot])
async def get_dbt_failures(
    service: ReachRadarService = Depends(get_reach_radar_service)
):
    """Get DBT failure hotspots."""
    return await service.get_dbt_failure_hotspots()

@router.get("/transitions", response_model=list[TransitionEntry])
async def get_transitions(
    service: ReachRadarService = Depends(get_reach_radar_service)
):
    """Get transition conversion rates."""
    return await service.get_transition_analysis()

@router.post("/run-analysis", response_model=CoverageAnalysisResult)
async def run_analysis(
    state: str | None = None,
    district: str | None = None,
    service: ReachRadarService = Depends(get_reach_radar_service)
):
    """Trigger a new coverage analysis."""
    return await service.run_coverage_analysis(state, district)

@router.get("/outreach/{institution_code}", response_model=OutreachList)
async def get_outreach_list(
    institution_code: str,
    service: ReachRadarService = Depends(get_reach_radar_service)
):
    """Get outreach list for a specific institution."""
    return await service.generate_outreach_list(institution_code)
