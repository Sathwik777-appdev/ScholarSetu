import inspect

from fastapi import APIRouter, Body, Depends, HTTPException

from app.dependencies import StudentPrincipal, get_skill_student, student_principal
from app.gateway.models import User
from app.ledger.service import LedgerService, get_ledger_service
from app.shared.types import MitraScope, SchemeType
from .rag import GuidelineRAG
from .schemas import GuidelineResult, JAGOMessageRequest, JAGOResponse
from .service import JAGOSkillService

router = APIRouter(prefix="/v1", tags=["JAGO Scholarship Skill"])

# Global singleton service for in-memory chat and tools
global_jago_service = JAGOSkillService(db=None)

# Tools whose student is injected from the authenticated session, never from the caller.
_STUDENT_SCOPED = {"get_applications", "get_pending_actions", "get_payments", "check_eligibility"}


def get_jago_service() -> JAGOSkillService:
    return global_jago_service


@router.post("/jago/chat", response_model=JAGOResponse)
async def chat_with_jago(
    request: JAGOMessageRequest,
    principal: StudentPrincipal = Depends(student_principal(MitraScope.VIEW_STATUS)),
    service: JAGOSkillService = Depends(get_jago_service),
):
    """In-app chat for the authenticated student."""
    return await service.process_message(
        student_id=principal.student_id,
        message=request.message,
        language=request.language or "hi",
        channel=request.channel or "app"
    )


@router.post("/skill/tools/{tool_name}")
async def invoke_tool(
    tool_name: str,
    parameters: dict = Body(default_factory=dict),
    student: User = Depends(get_skill_student),
    service: JAGOSkillService = Depends(get_jago_service),
    ledger: LedgerService = Depends(get_ledger_service),
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
        app = await ledger.get_application(str(kwargs.get("application_id", "")))
        if app is None or app.student_id != student.student_id:
            raise HTTPException(status_code=404, detail="Application not found")

    tool = service.tools[tool_name]
    try:
        inspect.signature(tool.handler).bind(**kwargs)
    except TypeError:
        raise HTTPException(status_code=422, detail=f"Invalid parameters for {tool_name}; expected {sorted(tool.parameters)}")
    result = await tool.handler(**kwargs)
    return {"tool": tool_name, "status": "success", "result": result}


@router.get("/jago/guidelines/search", response_model=list[GuidelineResult])
async def search_guidelines(
    query: str,
    scheme: SchemeType | None = None
):
    """Search public scheme guidelines (no personal data; no login needed)."""
    rag = GuidelineRAG()
    return await rag.search(query, scheme)
