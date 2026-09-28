import inspect
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.dependencies import StudentPrincipal, get_skill_student, student_principal
from app.gateway.models import User
from app.shared.types import MitraScope, SchemeType
from .schemas import GuidelineResult, JAGOMessageRequest, JAGOResponse
from .service import JAGOSkillService, get_jago_service

router = APIRouter(prefix="/v1", tags=["JAGO Scholarship Skill"])

# Tools whose student is injected from the authenticated session, never taken from the caller.
_STUDENT_SCOPED = {"get_applications", "get_pending_actions", "get_payments", "check_eligibility"}


@router.post("/jago/chat", response_model=JAGOResponse)
async def chat_with_jago(
    request: JAGOMessageRequest,
    principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
    service: JAGOSkillService = Depends(get_jago_service),
):
    """In-app chat. Answers are built only from ledger, eligibility and official-guideline tools."""
    return await service.process_message(principal.student_id, request.message, request.language,
                                         ai_assist=request.ai_assist and not principal.via_mitra)


@router.post("/skill/tools/{tool_name}")
async def invoke_tool(
    tool_name: str,
    parameters: dict = Body(default_factory=dict),
    student: User = Depends(get_skill_student),
    service: JAGOSkillService = Depends(get_jago_service),
):
    """Server-to-server tool calls from MoTA's JAGO.

    Requires X-Service-Token (JAGO's identity) and X-Student-Session (the student's own access
    token, obtained when the student logged in through JAGO). The student is taken only from
    that session; a student_id in the parameters is rejected.
    """
    if tool_name not in service.tools:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    if "student_id" in parameters:
        raise HTTPException(status_code=422, detail="student_id is taken from the student session, not parameters")

    kwargs = dict(parameters)
    if tool_name in _STUDENT_SCOPED:
        kwargs["student_id"] = student.student_id
    if tool_name == "get_timeline":
        app = await service.ledger.get_application(str(kwargs.get("application_id", "")))
        if app is None or app.student_id != student.student_id:
            raise HTTPException(status_code=404, detail="Application not found")
    if tool_name == "check_eligibility" and kwargs.get("scheme") not in {s.value for s in SchemeType}:
        raise HTTPException(status_code=422, detail=f"scheme must be one of {[s.value for s in SchemeType]}")

    tool = service.tools[tool_name]
    try:
        inspect.signature(tool.handler).bind(**kwargs)
    except TypeError:
        raise HTTPException(status_code=422, detail=f"Invalid parameters for {tool_name}; expected {sorted(tool.parameters)}")
    return {"tool": tool_name, "status": "success", "result": await tool.handler(**kwargs)}


@router.get("/jago/guidelines/search", response_model=list[GuidelineResult])
async def search_guidelines(
    query: str = Query(..., min_length=2, max_length=300),
    scheme: Optional[SchemeType] = None,
    service: JAGOSkillService = Depends(get_jago_service),
):
    """Search the official scheme guidelines (public text, no login). Empty when nothing is relevant enough."""
    return await service.search_guidelines(query, scheme.value if scheme else None)
