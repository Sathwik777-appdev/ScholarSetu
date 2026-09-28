from typing import Optional

from pydantic import BaseModel


class CoverageRow(BaseModel):
    district: str
    block: Optional[str]
    enrolled_st: int
    with_scholarship: int
    coverage_pct: float
    pvtg_enrolled: int
    pvtg_with_scholarship: int
    pvtg_coverage_pct: Optional[float]


class CoverageReport(BaseModel):
    level: str
    method: str
    matched_by_apaar: int
    matched_by_clk: int
    rows: list[CoverageRow]


class BottleneckRow(BaseModel):
    district: str
    state_name: str
    stage: str
    open_applications: int
    avg_days_in_stage: float
    sla_breaches: int


class DBTHotspotRow(BaseModel):
    state_name: str
    district: str
    applications_checked: int
    failing: int
    failure_rate_pct: float
    issue_counts: dict[str, int]


class TransitionRow(BaseModel):
    state_name: str
    district: str
    from_scheme: str
    to_scheme: str
    previous_year: str
    current_year: str
    eligible_cohort: int
    applied: int
    conversion_pct: Optional[float]


class OutreachStudent(BaseModel):
    record_ref: str
    class_: int
    pvtg: bool


class OutreachList(BaseModel):
    udise_code: str
    school_name: Optional[str]
    unreached_count: int
    students: Optional[list[OutreachStudent]]  # only for the school's own nodal officer
