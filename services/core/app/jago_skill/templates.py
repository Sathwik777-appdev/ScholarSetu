"""Deterministic response templates. Every amount, date and status in a JAGO answer is inserted here
from tool output; no text generator produces them."""

from app.nudge.service import SCHEME_NAMES

STATUS_DESCRIPTIONS = {
    "DRAFT": {"en": "draft (not yet submitted)", "hi": "ड्राफ्ट (अभी जमा नहीं हुआ)"},
    "SUBMITTED": {"en": "submitted, waiting for your institute", "hi": "जमा, संस्थान की प्रतीक्षा में"},
    "INSTITUTE_VERIFICATION": {"en": "being verified by your institute", "hi": "संस्थान द्वारा सत्यापन में"},
    "DEFICIENCY_RAISED": {"en": "returned to you: a deficiency needs your response", "hi": "आपको लौटाया गया: एक कमी का जवाब देना है"},
    "RESUBMITTED": {"en": "resubmitted, waiting for your institute", "hi": "दोबारा जमा, संस्थान की प्रतीक्षा में"},
    "AUTHORITY_VERIFICATION": {"en": "being verified by the district/state authority", "hi": "जिला/राज्य प्राधिकरण द्वारा सत्यापन में"},
    "SANCTIONED": {"en": "sanctioned", "hi": "स्वीकृत"},
    "PAYMENT_INITIATED": {"en": "payment sent to PFMS", "hi": "भुगतान PFMS को भेजा गया"},
    "CREDITED": {"en": "credited to your bank account", "hi": "आपके बैंक खाते में जमा"},
    "PAYMENT_FAILED": {"en": "payment failed", "hi": "भुगतान विफल"},
    "REJECTED": {"en": "rejected", "hi": "अस्वीकृत"},
    "RENEWAL_DUE": {"en": "due for renewal", "hi": "नवीनीकरण बाकी"},
}

T = {
    "status_line": {
        "en": "{scheme} {app_id} ({year}): {status} since {since}.",
        "hi": "{scheme} {app_id} ({year}): {since} से {status}।",
    },
    "next_action": {"en": "Next: {action}.", "hi": "आगे: {action}।"},
    "no_applications": {
        "en": "I could not find any scholarship application for you in ScholarSetu.",
        "hi": "ScholarSetu में आपका कोई छात्रवृत्ति आवेदन नहीं मिला।",
    },
    "money_line": {
        "en": "{scheme} {app_id}: sanctioned Rs {sanctioned}, credited Rs {credited}, pending Rs {pending}.",
        "hi": "{scheme} {app_id}: स्वीकृत ₹{sanctioned}, जमा ₹{credited}, बाकी ₹{pending}।",
    },
    "money_failed": {
        "en": "Rs {amount} (instalment {instalment}) failed: {reason}. Check your DBT status for the steps to fix it.",
        "hi": "₹{amount} (किस्त {instalment}) का भुगतान विफल: {reason}। सुधार के चरण DBT स्थिति में देखें।",
    },
    "money_in_transit": {
        "en": "Rs {amount} (instalment {instalment}) was sent to PFMS on {date}. The ledger has no credit date for it yet.",
        "hi": "₹{amount} (किस्त {instalment}) {date} को PFMS को भेजा गया। इसके जमा होने की तारीख अभी दर्ज नहीं है।",
    },
    "money_none_sanctioned": {
        "en": "{scheme} {app_id} is {status}. Nothing has been sanctioned yet, so no payment date exists yet.",
        "hi": "{scheme} {app_id} अभी {status} है। अभी कोई राशि स्वीकृत नहीं हुई है, इसलिए भुगतान की कोई तारीख नहीं है।",
    },
    "action_line": {"en": "- {description} (by {deadline})", "hi": "- {description} ({deadline} तक)"},
    "action_line_no_deadline": {"en": "- {description}", "hi": "- {description}"},
    "no_actions": {"en": "You have nothing pending right now.", "hi": "अभी आपका कोई काम बाकी नहीं है।"},
    "timeline_line": {"en": "- {date}: {event}", "hi": "- {date}: {event}"},
    "guideline_answer": {
        "en": "From the official guideline ({section}):\n\"{text}\"",
        "hi": "आधिकारिक दिशानिर्देश ({section}) के अनुसार:\n\"{text}\"",
    },
    "not_found": {
        "en": "I don't have this information. Please contact {helpline}.",
        "hi": "यह जानकारी मेरे पास नहीं है। कृपया {helpline} से संपर्क करें।",
    },
    "eligibility_result": {
        "en": "{scheme}: {verdict}. {reasons} (rules version {version})",
        "hi": "{scheme}: {verdict}। {reasons} (नियम संस्करण {version})",
    },
    "help": {
        "en": "I am JAGO, your scholarship assistant. Ask me about your application status, payments, pending actions, eligibility or scheme rules.",
        "hi": "मैं जागो हूँ, आपका छात्रवृत्ति सहायक। अपने आवेदन की स्थिति, भुगतान, बाकी काम, पात्रता या योजना के नियमों के बारे में पूछें।",
    },
    "language_fallback": {
        "en": "(This language is not supported yet; replying in Hindi.)",
        "hi": "(यह भाषा अभी उपलब्ध नहीं है; हिंदी में उत्तर दिया जा रहा है।)",
    },
}

EVENT_NAMES = {
    "ApplicationCreated": {"en": "application created", "hi": "आवेदन बना"},
    "ApplicationSubmitted": {"en": "submitted", "hi": "जमा किया"},
    "InstituteVerificationStarted": {"en": "institute verification started", "hi": "संस्थान सत्यापन शुरू"},
    "AuthorityVerificationStarted": {"en": "sent to district/state authority", "hi": "जिला/राज्य प्राधिकरण को भेजा"},
    "DeficiencyRaised": {"en": "deficiency raised", "hi": "कमी बताई गई"},
    "DeficiencyResponded": {"en": "you responded to the deficiency", "hi": "आपने कमी का जवाब दिया"},
    "Resubmitted": {"en": "resubmitted", "hi": "दोबारा जमा"},
    "Sanctioned": {"en": "sanctioned", "hi": "स्वीकृत"},
    "Rejected": {"en": "rejected", "hi": "अस्वीकृत"},
    "PaymentInitiated": {"en": "payment sent to PFMS", "hi": "भुगतान PFMS को भेजा"},
    "PaymentCredited": {"en": "payment credited", "hi": "भुगतान जमा"},
    "PaymentFailed": {"en": "payment failed", "hi": "भुगतान विफल"},
    "ReviewDecisionRecorded": {"en": "officer review decision", "hi": "अधिकारी समीक्षा निर्णय"},
    "RenewalDue": {"en": "renewal due", "hi": "नवीनीकरण बाकी"},
}

DEFICIENCY_EXPLANATIONS = {
    "INCOME_CERT_EXPIRED": {
        "en": "Your income certificate is not valid for the current financial year.",
        "hi": "आपका आय प्रमाण पत्र चालू वित्तीय वर्ष के लिए मान्य नहीं है।",
        "fix_steps": {"en": ["Apply for a new income certificate on your state e-District portal or at the block office",
                             "Upload it in the app, or pull it from DigiLocker"],
                      "hi": ["अपने राज्य के ई-डिस्ट्रिक्ट पोर्टल या प्रखंड कार्यालय में नया आय प्रमाण पत्र बनवाएँ",
                             "उसे ऐप में अपलोड करें या डिजीलॉकर से जोड़ें"]},
    },
    "ST_CERT_MISSING": {
        "en": "Your Scheduled Tribe certificate is missing or could not be verified.",
        "hi": "आपका अनुसूचित जनजाति प्रमाण पत्र नहीं मिला या सत्यापित नहीं हो सका।",
        "fix_steps": {"en": ["Check whether your caste certificate is in DigiLocker", "If not, upload a clear scan"],
                      "hi": ["देखें कि आपका जाति प्रमाण पत्र डिजीलॉकर में है या नहीं", "नहीं है तो उसकी साफ़ स्कैन कॉपी अपलोड करें"]},
    },
    "MARKSHEET_MISSING": {
        "en": "Your previous year's marksheet is required.",
        "hi": "पिछले वर्ष की अंकतालिका आवश्यक है।",
        "fix_steps": {"en": ["Pull the marksheet from DigiLocker", "Or upload a clear scan"],
                      "hi": ["अंकतालिका डिजीलॉकर से जोड़ें", "या उसकी साफ़ स्कैन कॉपी अपलोड करें"]},
    },
    "BANK_DETAILS_MISMATCH": {
        "en": "The name on your bank account does not match your identity records.",
        "hi": "आपके बैंक खाते का नाम आपके पहचान रिकॉर्ड से मेल नहीं खाता।",
        "fix_steps": {"en": ["Visit your bank branch with Aadhaar and passbook", "Ask them to correct the account name"],
                      "hi": ["आधार और पासबुक लेकर बैंक शाखा जाएँ", "खाते का नाम सुधारने को कहें"]},
    },
}


def scheme_name(scheme: str, lang: str) -> str:
    return SCHEME_NAMES.get(scheme, {}).get(lang, scheme)


def status_name(state: str, lang: str) -> str:
    return STATUS_DESCRIPTIONS.get(state, {}).get(lang, state)


def rupees(value: float) -> str:
    return f"{value:,.0f}"


# Next step per state, in both languages (the ledger's own next_action text is English-only).
NEXT_STEP = {
    "DRAFT": {"en": "review the pre-filled application and submit it", "hi": "पहले से भरा आवेदन जाँचकर जमा करें"},
    "SUBMITTED": {"en": "wait for your institute to start verification", "hi": "संस्थान द्वारा सत्यापन शुरू होने की प्रतीक्षा करें"},
    "INSTITUTE_VERIFICATION": {"en": "your institute is verifying it; nothing is needed from you", "hi": "संस्थान सत्यापन कर रहा है; आपको कुछ नहीं करना है"},
    "DEFICIENCY_RAISED": {"en": "respond to the deficiency (ask me 'what is missing?')", "hi": "कमी का जवाब दें (मुझसे पूछें 'क्या कमी है?')"},
    "RESUBMITTED": {"en": "wait for your institute to re-check your response", "hi": "संस्थान द्वारा आपके जवाब की जाँच की प्रतीक्षा करें"},
    "AUTHORITY_VERIFICATION": {"en": "the district/state authority is verifying it; nothing is needed from you", "hi": "जिला/राज्य प्राधिकरण सत्यापन कर रहा है; आपको कुछ नहीं करना है"},
    "SANCTIONED": {"en": "the payment will be sent to your bank account", "hi": "भुगतान आपके बैंक खाते में भेजा जाएगा"},
    "PAYMENT_INITIATED": {"en": "the payment has been sent to PFMS for transfer to your bank", "hi": "भुगतान आपके बैंक में भेजने के लिए PFMS को भेजा गया है"},
    "PAYMENT_FAILED": {"en": "check your DBT status for the steps to fix the payment", "hi": "भुगतान ठीक करने के चरण DBT स्थिति में देखें"},
    "RENEWAL_DUE": {"en": "renew your scholarship for the next academic year", "hi": "अगले शैक्षणिक वर्ष के लिए नवीनीकरण करें"},
    "REJECTED": {"en": "contact your institute's scholarship cell", "hi": "अपने संस्थान के छात्रवृत्ति प्रकोष्ठ से संपर्क करें"},
}

# Human-readable names for facts the eligibility engine may need.
FACT_LABELS = {
    "current_stage_known": {"en": "current class or course", "hi": "वर्तमान कक्षा या पाठ्यक्रम"},
    "current_class": {"en": "current class", "hi": "वर्तमान कक्षा"},
    "course_level": {"en": "course level", "hi": "पाठ्यक्रम स्तर"},
    "age": {"en": "date of birth", "hi": "जन्म तिथि"},
    "has_other_active_mota_scholarship": {"en": "current scholarship holdings", "hi": "वर्तमान छात्रवृत्ति"},
}
