from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import (
    CoverageAnalysisResult,
    CoverageHeatmapEntry,
    BottleneckEntry,
    DBTFailureHotspot,
    TransitionEntry,
    OutreachList
)
from .pprl import BloomFilterEncoder, PPRLMatcher

class ReachRadarService:
    """Privacy-preserving coverage gap discovery."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def run_coverage_analysis(self, state: str | None = None, district: str | None = None) -> CoverageAnalysisResult:
        """Run full coverage analysis.
        1. Fetch enrolled ST students from UDISE+/APAAR mocks
        2. Fetch scholarship holders from ledger
        3. Encode both sets using PPRL
        4. Match and find gaps
        5. Compute coverage metrics
        6. Generate outreach lists (sent only to own institution)
        """
        # Mock implementation
        encoder = BloomFilterEncoder()
        matcher = PPRLMatcher(threshold=0.85)
        
        # Encodings simulated
        return CoverageAnalysisResult(
            total_enrolled=10000,
            total_scholarship=6500,
            coverage_pct=65.0,
            by_district={"District A": 70.0, "District B": 60.0},
            by_scheme={"PRE_MATRIC": 80.0, "POST_MATRIC": 50.0}
        )
    
    async def get_coverage_heatmap(self, level: str = "district") -> list[CoverageHeatmapEntry]:
        """Get coverage percentage by geography for ministry dashboard."""
        return [
            CoverageHeatmapEntry(
                state="Maharashtra",
                district="Palghar",
                block="Dahanu",
                coverage_pct=55.4,
                pvtg_coverage_pct=30.2,
                total_enrolled=5000,
                total_scholarship=2770
            )
        ]
    
    async def get_bottleneck_analysis(self) -> list[BottleneckEntry]:
        """Find where applications are stuck longest."""
        return [
            BottleneckEntry(
                state="Odisha",
                district="Mayurbhanj",
                stage="INSTITUTE_VERIFICATION",
                avg_days_stuck=45.5,
                count=1200
            )
        ]
    
    async def get_dbt_failure_hotspots(self) -> list[DBTFailureHotspot]:
        """Find districts with highest DBT failure rates."""
        return [
            DBTFailureHotspot(
                district="Bastar",
                failure_count=450,
                failure_rate=12.5,
                common_failure_codes=["BANK_ACCOUNT_INACTIVE", "AADHAAR_NOT_MAPPED"]
            )
        ]
    
    async def get_transition_analysis(self) -> list[TransitionEntry]:
        """Analyze transition rates (e.g., Class 10 → Post-Matric conversion)."""
        return [
            TransitionEntry(
                from_scheme="PRE_MATRIC",
                to_scheme="POST_MATRIC",
                eligible_count=5000,
                applied_count=2000,
                conversion_rate=40.0
            )
        ]
    
    async def generate_outreach_list(self, institution_code: str) -> OutreachList:
        """Generate outreach list for a specific institution.
        Contains only students of THAT institution."""
        return OutreachList(
            institution_code=institution_code,
            institution_name=f"Institution {institution_code}",
            unreached_students_count=45,
            sent_to=f"nodal_officer_{institution_code}@edu.in"
        )
