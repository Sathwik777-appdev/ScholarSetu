from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.types import SchemeType
from .tools import ToolDefinition, Intent, INTENT_PATTERNS
from .schemas import JAGOResponse, ToolCallLog, GuidelineResult
from .templates import RESPONSE_TEMPLATES, STATUS_DESCRIPTIONS, DEFICIENCY_EXPLANATIONS
from .rag import GuidelineRAG

class JAGOSkillService:
    """JAGO Scholarship Skill - tool-grounded assistant for scholarship queries.
    
    Key principle: Money amounts, dates, and statuses ONLY come from tool outputs
    and are rendered through deterministic templates. The LLM never generates these.
    """
    
    def __init__(self, db: AsyncSession, ledger_service: Any = None, eligibility_service: Any = None, attestation_service: Any = None):
        self.db = db
        self.ledger_service = ledger_service
        self.eligibility_service = eligibility_service
        self.attestation_service = attestation_service
        self.tools = self._register_tools()
        self.rag = GuidelineRAG()
    
    def _register_tools(self) -> dict[str, ToolDefinition]:
        """Register all tools that the LLM can call."""
        return {
            "get_applications": ToolDefinition(
                name="get_applications",
                description="Get all scholarship applications for the authenticated student",
                parameters={"student_id": "string"},
                handler=self._get_applications
            ),
            "get_timeline": ToolDefinition(
                name="get_timeline",
                description="Get the event history/timeline for a specific application",
                parameters={"application_id": "string"},
                handler=self._get_timeline
            ),
            "get_pending_actions": ToolDefinition(
                name="get_pending_actions",
                description="Get list of pending actions (deficiencies, expiring attestations) for student",
                parameters={"student_id": "string"},
                handler=self._get_pending_actions
            ),
            "get_payments": ToolDefinition(
                name="get_payments",
                description="Get payment details (sanctioned/credited/failed amounts) for student",
                parameters={"student_id": "string"},
                handler=self._get_payments
            ),
            "check_eligibility": ToolDefinition(
                name="check_eligibility",
                description="Check if student is eligible for a specific scheme",
                parameters={"student_id": "string", "scheme": "SchemeType"},
                handler=self._check_eligibility
            ),
            "explain_deficiency": ToolDefinition(
                name="explain_deficiency",
                description="Explain a deficiency code in plain language with fix steps",
                parameters={"deficiency_code": "string"},
                handler=self._explain_deficiency
            ),
            "search_guidelines": ToolDefinition(
                name="search_guidelines",
                description="Search official scheme guidelines for information",
                parameters={"query": "string"},
                handler=self._search_guidelines
            ),
        }
    
    async def process_message(self, student_id: str, message: str, language: str = "hi", channel: str = "app") -> JAGOResponse:
        """Process a student message.
        1. Detect intent from the message
        2. Determine which tools to call
        3. Call tools and get factual data
        4. Compose response using templates for factual parts
        5. Log conversation
        """
        intent = await self._detect_intent(message)
        response_text = ""
        tool_calls = []
        
        # Tool routing based on intent (simplified for prototype)
        if intent == Intent.STATUS_CHECK:
            app_data = await self._get_applications(student_id)
            tool_calls.append(ToolCallLog(tool_name="get_applications", parameters={"student_id": student_id}, result_summary="Found applications"))
            
            if app_data and "applications" in app_data and app_data["applications"]:
                app = app_data["applications"][0]
                status_desc = STATUS_DESCRIPTIONS.get(app.get("status", ""), {}).get(language, app.get("status", ""))
                response_text = RESPONSE_TEMPLATES["status_update"][language].format(
                    scheme_name=app.get("scheme_name", "Scholarship"),
                    app_id=app.get("id", "Unknown"),
                    status=status_desc,
                    next_action=""
                )
            else:
                response_text = RESPONSE_TEMPLATES["no_data"][language].format(helpline_number="1800-111-222")

        elif intent == Intent.PAYMENT_INFO:
            payment_data = await self._get_payments(student_id)
            tool_calls.append(ToolCallLog(tool_name="get_payments", parameters={"student_id": student_id}, result_summary="Found payments"))
            if payment_data:
                response_text = RESPONSE_TEMPLATES["payment_summary"][language].format(
                    scheme_name=payment_data.get("scheme_name", "Scholarship"),
                    academic_year=payment_data.get("academic_year", "2023-24"),
                    sanctioned=payment_data.get("sanctioned", 0),
                    credited=payment_data.get("credited", 0),
                    pending=payment_data.get("pending", 0),
                    status_detail=""
                )
            else:
                response_text = RESPONSE_TEMPLATES["no_data"][language].format(helpline_number="1800-111-222")

        elif intent == Intent.ELIGIBILITY_QUERY:
            response_text = RESPONSE_TEMPLATES["eligibility_result"][language].format(
                scheme_name="Scholarship",
                result="You may be eligible based on basic criteria.",
                reasons="Please check detailed guidelines."
            )
            
        elif intent == Intent.GUIDELINE_QUERY:
            guidelines = await self._search_guidelines(message)
            tool_calls.append(ToolCallLog(tool_name="search_guidelines", parameters={"query": message}, result_summary=f"Found {len(guidelines)} results"))
            if guidelines:
                response_text = "\n\n".join([f"{g['section']}: {g['content']}" for g in guidelines])
            else:
                response_text = RESPONSE_TEMPLATES["no_data"][language].format(helpline_number="1800-111-222")

        elif intent == Intent.DEFICIENCY_HELP:
            deficiency_data = await self._explain_deficiency("INCOME_CERT_EXPIRED") # Mock
            tool_calls.append(ToolCallLog(tool_name="explain_deficiency", parameters={"deficiency_code": "INCOME_CERT_EXPIRED"}, result_summary="Explained deficiency"))
            if deficiency_data:
                response_text = RESPONSE_TEMPLATES["deficiency_explanation"][language].format(
                    description=deficiency_data.get("description", ""),
                    fix_steps="\n".join([f"- {s}" for s in deficiency_data.get("fix_steps", [])]),
                    deadline="15 days from notice"
                )
            else:
                response_text = RESPONSE_TEMPLATES["no_data"][language].format(helpline_number="1800-111-222")
                
        else:
            response_text = RESPONSE_TEMPLATES["greeting"][language]

        return JAGOResponse(
            response_text=response_text,
            tool_calls_made=tool_calls,
            citations=[],
            suggested_actions=[]
        )
    
    async def _detect_intent(self, message: str) -> Intent:
        """Detect user intent from message."""
        msg_lower = message.lower()
        for intent, patterns in INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in msg_lower:
                    return intent
        return Intent.GENERAL_HELP
    
    # Tool handler implementations
    async def _get_applications(self, student_id: str) -> dict: 
        return {"applications": [{"id": "APP123", "scheme_name": "Post Matric", "status": "INSTITUTE_VERIFICATION"}]}
    
    async def _get_timeline(self, application_id: str) -> dict: 
        return {"timeline": []}
    
    async def _get_pending_actions(self, student_id: str) -> dict: 
        return {"actions": []}
    
    async def _get_payments(self, student_id: str) -> dict: 
        return {"scheme_name": "Post Matric", "academic_year": "2023-24", "sanctioned": 12000, "credited": 12000, "pending": 0}
    
    async def _check_eligibility(self, student_id: str, scheme: str) -> dict: 
        return {"eligible": True}
    
    async def _explain_deficiency(self, deficiency_code: str) -> dict: 
        if deficiency_code in DEFICIENCY_EXPLANATIONS:
            return {
                "description": DEFICIENCY_EXPLANATIONS[deficiency_code]["en"],
                "fix_steps": DEFICIENCY_EXPLANATIONS[deficiency_code].get("fix_steps", [])
            }
        return {}
    
    async def _search_guidelines(self, query: str) -> dict: 
        results = await self.rag.search(query)
        return [{"section": r.section, "content": r.content, "source": r.source} for r in results]
