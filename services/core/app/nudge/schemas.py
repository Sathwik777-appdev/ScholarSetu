from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.shared.types import NotificationChannel


class NotificationOut(BaseModel):
    id: str
    student_id: Optional[str]
    template_key: str
    channel: NotificationChannel
    language: str
    body: str
    data: dict[str, Any]
    created_at: datetime
    read_at: Optional[datetime]
