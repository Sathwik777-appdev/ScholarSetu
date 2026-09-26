"""Intent routing for JAGO (rule-based and deterministic; see ARCHITECTURE.md §19 deviations).

Order matters: money is checked before status, so "Mera paisa kab aayega?" is a payment question
even though "kab" (when) also appears in status questions.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class Intent(str, Enum):
    DEFICIENCY_HELP = "deficiency_help"
    PAYMENT_INFO = "payment_info"
    ELIGIBILITY_QUERY = "eligibility_query"
    GUIDELINE_QUERY = "guideline_query"
    TIMELINE_QUERY = "timeline_query"
    STATUS_CHECK = "status_check"
    GENERAL_HELP = "general_help"


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, str]
    handler: Callable


def _any(*words: str) -> re.Pattern:
    return re.compile("|".join(words), re.IGNORECASE)


# Personal-money cues. A general question about scheme amounts ("how much is the stipend") is a guideline query.
_MONEY = _any(r"\bpaisa\b", r"\bpaise\b", r"\bpayment", r"\bcredited\b", r"\bcredit\b", r"\bdbt\b", r"bhugtan",
              r"\brupa?ye\b", r"\brupees?\b", r"\bmoney\b", r"received", r"\bmila\b", r"\bmile\b", r"kab aayeg",
              r"kab ayeg", r"kab milega", r"पैसा", r"पैसे", r"भुगतान", r"रुपये", r"राशि कब", r"कब आएगा", r"कब मिलेगा",
              r"my (scholarship )?amount", r"bank (me|mein|में)")
_GENERAL_AMOUNT = _any(r"how much is", r"what is the (amount|stipend|value)", r"kitna milta", r"kitni milti",
                       r"scholarship amount for", r"rate of", r"कितना मिलता", r"कितनी मिलती")
_DEFICIENCY = _any(r"deficien", r"\bkami\b", r"कमी", r"missing document", r"document (missing|required)",
                   r"dastaveez", r"दस्तावेज़? (कम|चाहिए)", r"objection", r"returned to student", r"defect")
_ELIGIBILITY = _any(r"\bam i eligible", r"\bcan i apply", r"eligible for me", r"\bkya (main|mai|mein) .*(apply|patra|eligible)",
                    r"\bpatra\s*(hu|hoon|hun)", r"\bmain patra", r"क्या मैं .*(पात्र|आवेदन)", r"मैं पात्र", r"eligibility check")
_GUIDELINE = _any(r"\blimit\b", r"\bceiling\b", r"\brule", r"\bcriteria\b", r"guideline", r"\bniyam", r"नियम", r"सीमा",
                  r"who (is|are) eligible", r"eligibility (for|of)", r"income (limit|criteria|ceiling)", r"age limit",
                  r"documents? required", r"how to apply", r"\bstipend\b", r"\bfellowship amount", r"kaun patra",
                  r"कौन पात्र", r"जानकारी", r"jankari", r"what is (the )?(pre|post)[ -]?matric", r"duration")
_TIMELINE = _any(r"timeline", r"history", r"itihas", r"इतिहास", r"kya kya hua", r"क्या क्या हुआ", r"all events",
                 r"sab kuch")
_STATUS = _any(r"status", r"\bkab\b", r"\bwhen\b", r"kya hua", r"kahan tak", r"progress", r"pending", r"approved",
               r"sanction", r"rejected", r"where is my", r"स्थिति", r"कब", r"क्या हुआ", r"कहाँ तक", r"application")


def detect_intent(message: str) -> Intent:
    text = message.strip()
    if _DEFICIENCY.search(text):
        return Intent.DEFICIENCY_HELP
    if _MONEY.search(text) and not _GENERAL_AMOUNT.search(text):
        return Intent.PAYMENT_INFO
    if _ELIGIBILITY.search(text):
        return Intent.ELIGIBILITY_QUERY
    if _GUIDELINE.search(text) or _GENERAL_AMOUNT.search(text):
        return Intent.GUIDELINE_QUERY
    if _TIMELINE.search(text):
        return Intent.TIMELINE_QUERY
    if _STATUS.search(text):
        return Intent.STATUS_CHECK
    return Intent.GENERAL_HELP
