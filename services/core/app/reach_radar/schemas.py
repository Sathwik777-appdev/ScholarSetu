from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class CoverageAnalysisResult(BaseModel):
    total_enrolled: int
    total_scholarship: int
    coverage_pct: float
    by_district: dict[str, float]
    by_scheme: dict[str, float]

class CoverageHeatmapEntry(BaseModel):
    state: str
    district: str
    block: str
    coverage_pct: float
    pvtg_coverage_pct: float
    total_enrolled: int
    total_scholarship: int

class BottleneckEntry(BaseModel):
    state: str
    district: str
    stage: str
    avg_days_stuck: float
    count: int

class DBTFailureHotspot(BaseModel):
    district: str
    failure_count: int
    failure_rate: float
    common_failure_codes: list[str]

class TransitionEntry(BaseModel):
    from_scheme: str
    to_scheme: str
    eligible_count: int
    applied_count: int
    conversion_rate: float

class OutreachList(BaseModel):
    institution_code: str
    institution_name: str
    unreached_students_count: int
    sent_to: str
