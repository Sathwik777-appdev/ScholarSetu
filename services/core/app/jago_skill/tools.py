from enum import Enum
from dataclasses import dataclass
from typing import Callable

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, str]
    handler: Callable

class Intent(str, Enum):
    STATUS_CHECK = "status_check"
    PAYMENT_INFO = "payment_info"
    ELIGIBILITY_QUERY = "eligibility_query"
    DEFICIENCY_HELP = "deficiency_help"
    GUIDELINE_QUERY = "guideline_query"
    TIMELINE_QUERY = "timeline_query"
    GENERAL_HELP = "general_help"

# Intent detection patterns (keyword-based for prototype, can be upgraded to ML)
INTENT_PATTERNS = {
    Intent.STATUS_CHECK: [
        "status", "kab", "when", "kya hua", "kahan tak", "progress",
        "pending", "approved", "rejected", "processed",
        "स्थिति", "कब", "क्या हुआ", "कहाँ तक"
    ],
    Intent.PAYMENT_INFO: [
        "paisa", "payment", "money", "amount", "credited", "received",
        "kitna", "rupees", "bank", "dbt", "bhugtan",
        "पैसा", "भुगतान", "कितना", "बैंक"
    ],
    Intent.ELIGIBILITY_QUERY: [
        "eligible", "apply", "patra", "qualification", "can i",
        "am i", "criteria", "yogya", "पात्र", "योग्य", "आवेदन"
    ],
    Intent.DEFICIENCY_HELP: [
        "deficiency", "document", "upload", "kami", "missing",
        "required", "dastaveez", "दस्तावेज़", "कमी"
    ],
    Intent.GUIDELINE_QUERY: [
        "rule", "guideline", "limit", "income", "niyam",
        "information", "detail", "about", "jankari",
        "नियम", "जानकारी", "सीमा"
    ],
    Intent.TIMELINE_QUERY: [
        "timeline", "history", "events", "itihas", "kya kya hua",
        "इतिहास", "क्या क्या हुआ"
    ],
}
