from typing import Any, Optional

from pydantic import BaseModel, Field


class JAGOMessageRequest(BaseModel):
    model_config = {"extra": "forbid"}
    message: str = Field(..., min_length=1, max_length=1000)
    language: str = Field("hi", max_length=10)
    channel: str = Field("app", pattern=r"^(app|web|whatsapp|voice|sms)$")


class Citation(BaseModel):
    source: str
    section: str
    url: str
    effective: str


class ToolCallLog(BaseModel):
    tool_name: str
    parameters: dict[str, Any]
    result_summary: Optional[str] = None


class JAGOResponse(BaseModel):
    response_text: str
    intent: str
    language: str
    language_note: Optional[str] = None
    tool_calls_made: list[ToolCallLog] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class GuidelineResult(BaseModel):
    scheme: str
    section: str
    content: str
    source: str
    url: str
    effective: str
    relevance_score: float
