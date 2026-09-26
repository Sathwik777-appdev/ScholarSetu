from typing import Protocol, Any
from app.shared.types import SourceSystem, CanonicalState, PaymentState
from pydantic import BaseModel

class ExternalApplication(BaseModel):
    ref_id: str
    student_ref: str
    status: str
    details: dict[str, Any]

class ExternalStatus(BaseModel):
    status_code: str
    remarks: str
    updated_at: str

class ExternalPayment(BaseModel):
    payment_id: str
    amount: float
    status: PaymentState
    date: str

class SchemeAdapter(Protocol):
    source_system: SourceSystem
    
    async def fetch_applications(self, student_ref: str) -> list[ExternalApplication]: ...
    async def fetch_status(self, app_ref: str) -> ExternalStatus: ...
    async def fetch_payments(self, app_ref: str) -> list[ExternalPayment]: ...
    async def submit_deficiency_response(self, app_ref: str, deficiency_id: str, response: dict) -> bool: ...
    async def map_state(self, external_state: str) -> CanonicalState: ...
