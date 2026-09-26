"""Phase 5: JAGO intent routing. Money is checked before status."""

import pytest

from app.jago_skill.tools import Intent, detect_intent

CASES = [
    # money (personal) — must win over status words like "kab"/"when"
    ("Mera paisa kab aayega?", Intent.PAYMENT_INFO),
    ("mera paisa kab milega", Intent.PAYMENT_INFO),
    ("When will I get my payment?", Intent.PAYMENT_INFO),
    ("Has my scholarship been credited?", Intent.PAYMENT_INFO),
    ("DBT status batao", Intent.PAYMENT_INFO),
    ("मेरा पैसा कब आएगा?", Intent.PAYMENT_INFO),
    ("भुगतान हुआ या नहीं", Intent.PAYMENT_INFO),
    ("kitne rupaye mile abhi tak", Intent.PAYMENT_INFO),
    ("bank me paise aaye kya", Intent.PAYMENT_INFO),
    # status
    ("Meri application ka status kya hai?", Intent.STATUS_CHECK),
    ("What is the status of my application?", Intent.STATUS_CHECK),
    ("मेरे आवेदन की स्थिति क्या है", Intent.STATUS_CHECK),
    ("application kahan tak pahunchi", Intent.STATUS_CHECK),
    ("Is my application approved?", Intent.STATUS_CHECK),
    # deficiency
    ("Mere form me kya kami hai?", Intent.DEFICIENCY_HELP),
    ("What deficiency was raised on my application?", Intent.DEFICIENCY_HELP),
    ("मेरे आवेदन में क्या कमी है", Intent.DEFICIENCY_HELP),
    # eligibility (personal)
    ("Am I eligible for Post Matric scholarship?", Intent.ELIGIBILITY_QUERY),
    ("kya main NFST ke liye apply kar sakti hoon", Intent.ELIGIBILITY_QUERY),
    ("क्या मैं टॉप क्लास के लिए पात्र हूँ", Intent.ELIGIBILITY_QUERY),
    # guidelines (general rules, including general amount questions)
    ("What is the income limit for post matric?", Intent.GUIDELINE_QUERY),
    ("पोस्ट मैट्रिक छात्रवृत्ति के लिए आय सीमा क्या है", Intent.GUIDELINE_QUERY),
    ("How much is the stipend for hostellers under pre matric?", Intent.GUIDELINE_QUERY),
    ("What is the age limit for overseas scholarship?", Intent.GUIDELINE_QUERY),
    ("Top class scholarship ke niyam kya hain", Intent.GUIDELINE_QUERY),
    # timeline
    ("Show me the history of my application", Intent.TIMELINE_QUERY),
    ("ab tak kya kya hua", Intent.TIMELINE_QUERY),
    # help
    ("namaste", Intent.GENERAL_HELP),
]


def test_at_least_twenty_utterances():
    assert len(CASES) >= 20


@pytest.mark.parametrize("message,intent", CASES)
def test_routing(message, intent):
    assert detect_intent(message) == intent, message
