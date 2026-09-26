import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.shared.types import SourceSystem, CanonicalState, PaymentState
from app.adapters.base import SchemeAdapter, ExternalApplication, ExternalStatus, ExternalPayment
from app.adapters.state_mapping import StateMapper
from pathlib import Path

class SFMPAdapter(SchemeAdapter):
    source_system = SourceSystem.SFMP
    
    def __init__(self, base_url: str = "http://mock-sfmp.local/api"):
        self.base_url = base_url
        yaml_path = Path(__file__).parents[4] / "adapters" / "sfmp" / "state_map.yaml"
        self.mapper = StateMapper(str(yaml_path))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_applications(self, student_ref: str) -> list[ExternalApplication]:
        async with httpx.AsyncClient() as client:
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_status(self, app_ref: str) -> ExternalStatus:
        async with httpx.AsyncClient() as client:
            return ExternalStatus(status_code="NEW", remarks="", updated_at="")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_payments(self, app_ref: str) -> list[ExternalPayment]:
        async with httpx.AsyncClient() as client:
            return []

    async def submit_deficiency_response(self, app_ref: str, deficiency_id: str, response: dict) -> bool:
        return True

    async def map_state(self, external_state: str) -> CanonicalState:
        return self.mapper.map_state(external_state)
