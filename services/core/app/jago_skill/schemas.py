from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class JAGOMessageRequest(BaseModel):
    message: str
    language: str = "hi"
    channel: str = "app"
    
class Citation(BaseModel):
    source: str
    content: str
    
class SuggestedAction(BaseModel):
    label: str
    action_type: str
    value: str

class ToolCallLog(BaseModel):
    tool_name: str
    parameters: dict[str, Any]
    result_summary: str | None = None

class JAGOResponse(BaseModel):
    response_text: str
    tool_calls_made: list[ToolCallLog] = []
    citations: list[Citation] = []
    suggested_actions: list[SuggestedAction] = []

class GuidelineResult(BaseModel):
    section: str
    content: str
    source: str
    relevance_score: float = 0.0
