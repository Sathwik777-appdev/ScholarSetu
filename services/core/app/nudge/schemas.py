from pydantic import BaseModel, Field
from typing import Dict, Any, List
from app.shared.types import NotificationChannel

class NotificationRequest(BaseModel):
    user_id: str
    template_key: str
    params: Dict[str, Any]
    channels: List[NotificationChannel]
    language: str = "hi"

class NotificationResponse(BaseModel):
    status: str
    message: str

class EscalationStatus(BaseModel):
    application_id: str
    current_stage: str
    days_stuck: int
    escalated_to: str
