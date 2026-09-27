"""Nudge & Notification Engine (ARCHITECTURE.md §6.10).

Consumes ledger events, decides who to tell and in which language, and records one notification
per recipient and channel. In-app (PUSH) notifications are stored for the app to fetch; critical
alerts are also sent by SMS through the (simulated) SMS gateway. Redelivered events are ignored.
"""

import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.gateway.models import User
from app.gateway.service import send_sms
from app.nudge.models import Notification
from app.shared.events import BaseEvent
from app.shared.ids import new_id
from app.shared.types import NotificationChannel, UserRole
from app.students.models import Student

logger = logging.getLogger("scholarsetu.nudge")

SUPPORTED_LANGUAGES = ("hi", "en")

SCHEME_NAMES = {
    "PRE_MATRIC": {"en": "Pre-Matric Scholarship", "hi": "प्री-मैट्रिक छात्रवृत्ति"},
    "POST_MATRIC": {"en": "Post-Matric Scholarship", "hi": "पोस्ट-मैट्रिक छात्रवृत्ति"},
    "TOP_CLASS": {"en": "Top Class Education Scholarship", "hi": "टॉप क्लास शिक्षा छात्रवृत्ति"},
    "NFST": {"en": "National Fellowship for ST Students", "hi": "एसटी छात्रों के लिए राष्ट्रीय फ़ेलोशिप"},
    "NOS": {"en": "National Overseas Scholarship", "hi": "राष्ट्रीय प्रवासी छात्रवृत्ति"},
}

TEMPLATES = {
    "FORWARDED_TO_AUTHORITY": {
        "en": "{name}: your {scheme} application {app_id} was verified by your institute and sent to the district/state authority.",
        "hi": "{name}: आपका {scheme} आवेदन {app_id} संस्थान द्वारा सत्यापित होकर जिला/राज्य प्राधिकरण को भेजा गया है।",
    },
    "DEFICIENCY_RAISED": {
        "en": "{name}: action needed on {app_id}: {description}. Please respond by {due}.",
        "hi": "{name}: आवेदन {app_id} पर कार्रवाई आवश्यक: {description}। कृपया {due} तक जवाब दें।",
    },
    "SANCTIONED": {
        "en": "{name}: your {scheme} ({app_id}) is sanctioned. Total amount: Rs {amount}.",
        "hi": "{name}: आपकी {scheme} ({app_id}) स्वीकृत हो गई है। कुल राशि: ₹{amount}।",
    },
    "CREDITED": {
        "en": "{name}: Rs {amount} for {scheme} ({app_id}) has been credited to your bank account.",
        "hi": "{name}: {scheme} ({app_id}) के ₹{amount} आपके बैंक खाते में जमा हो गए हैं।",
    },
    "PAYMENT_FAILED": {
        "en": "{name}: the payment of Rs {amount} for {app_id} failed ({reason}). Open the app for the steps to fix it.",
        "hi": "{name}: {app_id} का ₹{amount} का भुगतान विफल रहा ({reason})। सुधार के चरण ऐप में देखें।",
    },
    "RENEWAL_DUE": {
        "en": "{name}: your {scheme} is due for renewal. Apply for the next academic year.",
        "hi": "{name}: आपकी {scheme} का नवीनीकरण बाकी है। अगले शैक्षणिक वर्ष के लिए आवेदन करें।",
    },
    "DBT_ACTION_NEEDED": {
        "en": "{name}: your scholarship payment cannot reach your bank account yet ({reason}). Open the app for the steps to fix it.",
        "hi": "{name}: आपकी छात्रवृत्ति का भुगतान अभी आपके बैंक खाते में नहीं पहुँच सकता ({reason})। सुधार के चरण ऐप में देखें।",
    },
    "SLA_BREACH_STUDENT": {
        "en": "{name}: your {scheme} application {app_id} has been at the {stage} stage for {waited}, longer than the {target} it should take. We have reminded the {tier}.",
        "hi": "{name}: आपका {scheme} आवेदन {app_id} {waited} से {stage} चरण पर है, जबकि इसमें {target} लगने चाहिए। हमने {tier} को याद दिलाया है।",
    },
    "SLA_BREACH_OFFICER": {
        "en": "Reminder: {count} application(s) in your jurisdiction are past their target time at {stage}. Latest: {app_id} ({student}), waiting {waited} against a target of {target}. Please act on them.",
        "hi": "अनुस्मारक: आपके क्षेत्र के {count} आवेदन {stage} पर तय समय से अधिक लंबित हैं। नवीनतम: {app_id} ({student}), {waited} से लंबित; लक्ष्य {target}। कृपया कार्रवाई करें।",
    },
    "TRANSITION_DETECTED": {
        "en": "{name}: you may be eligible for the {scheme}. A pre-filled application ({app_id}) is ready for you to check and submit.",
        "hi": "{name}: आप {scheme} के लिए पात्र हो सकते हैं। पहले से भरा आवेदन ({app_id}) जाँचने और जमा करने के लिए तैयार है।",
    },
    "REVIEW_INFO_REQUESTED": {
        "en": "{name}: an officer needs more information about your {claim} for {app_id}.",
        "hi": "{name}: अधिकारी को {app_id} के लिए आपके {claim} के बारे में और जानकारी चाहिए।",
    },
}

# event type -> (template, critical?)
EVENT_TEMPLATES = {
    "AuthorityVerificationStarted": ("FORWARDED_TO_AUTHORITY", False),
    "DeficiencyRaised": ("DEFICIENCY_RAISED", True),
    "Sanctioned": ("SANCTIONED", False),
    "PaymentCredited": ("CREDITED", True),
    "PaymentFailed": ("PAYMENT_FAILED", True),
    "RenewalDue": ("RENEWAL_DUE", False),
    "TransitionDetected": ("TRANSITION_DETECTED", False),
    "SLABreached": ("SLA_BREACH_STUDENT", False),
}

TIER_NAMES = {"INSTITUTE_OFFICER": {"en": "institute's scholarship officer", "hi": "संस्थान के छात्रवृत्ति अधिकारी"},
              "DISTRICT_OFFICER": {"en": "district welfare officer", "hi": "जिला कल्याण अधिकारी"},
              "STATE_OFFICER": {"en": "state tribal welfare department", "hi": "राज्य जनजातीय कल्याण विभाग"}}
STAGE_NAMES = {"SUBMITTED": {"en": "submission", "hi": "जमा"},
               "INSTITUTE_VERIFICATION": {"en": "institute verification", "hi": "संस्थान सत्यापन"},
               "RESUBMITTED": {"en": "re-check by institute", "hi": "संस्थान द्वारा पुनः जाँच"},
               "AUTHORITY_VERIFICATION": {"en": "district/state verification", "hi": "जिला/राज्य सत्यापन"},
               "SANCTIONED": {"en": "payment release", "hi": "भुगतान जारी"},
               "PAYMENT_INITIATED": {"en": "bank credit", "hi": "बैंक में जमा"},
               "PAYMENT_FAILED": {"en": "payment retry", "hi": "भुगतान पुनः प्रयास"}}


def render(template_key: str, language: str, params: dict[str, Any]) -> str:
    template = TEMPLATES[template_key]
    return template.get(language, template["en"]).format(**params)


def duration(days: float, lang: str) -> str:
    """Human-readable duration ("9 days", "3 hours", "1 minute"), in English or Hindi."""
    units = [(1.0, "day", "दिन"), (1 / 24, "hour", "घंटे"), (1 / 1440, "minute", "मिनट")]
    for size, en, hi in units:
        if days >= size or size == units[-1][0]:
            n = max(1, round(days / size))
            return f"{n} {hi}" if lang == "hi" else f"{n} {en}{'' if n == 1 else 's'}"
    return ""


def _amount(value: Any) -> str:
    return f"{float(value):,.0f}" if value is not None else "-"


class NudgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _template_for(self, event: BaseEvent) -> Optional[tuple[str, bool]]:
        if event.type == "DBTHealthChecked":
            return ("DBT_ACTION_NEEDED", True) if event.payload.get("status") == "FAIL" else None
        if event.type == "ReviewDecisionRecorded" and event.payload.get("decision") == "REQUEST_INFO":
            return "REVIEW_INFO_REQUESTED", False
        return EVENT_TEMPLATES.get(event.type)

    async def recipients(self, student: Student) -> list[User]:
        """The student and, for household members, the guardian."""
        query = select(User).where(User.is_active.is_(True), User.student_id == student.id)
        users = list((await self.db.execute(query)).scalars())
        if student.household_id:
            users += list((await self.db.execute(select(User).where(
                User.is_active.is_(True), User.role == UserRole.GUARDIAN,
                User.household_id == student.household_id))).scalars())
        return users

    async def handle_event(self, event: BaseEvent) -> int:
        """Create the notifications an event calls for. Returns how many new ones were stored."""
        match = self._template_for(event)
        student_id = event.payload.get("student_id")
        if match is None or not student_id:
            return 0
        student = await self.db.get(Student, student_id)
        if student is None:
            logger.warning("event %s refers to unknown student %s", event.event_id, student_id)
            return 0
        template_key, critical = match
        language = student.preferred_language if student.preferred_language in SUPPORTED_LANGUAGES else "hi"
        p = event.payload
        params = {
            "name": student.full_name.split()[0],
            "app_id": p.get("application_id", ""),
            "scheme": SCHEME_NAMES.get(p.get("scheme", ""), {}).get(language, p.get("scheme", "")),
            "amount": _amount(p.get("total_amount", p.get("amount"))),
            "description": p.get("description", ""),
            "due": (p.get("due_at") or "")[:10],
            "reason": p.get("failure_code") or ", ".join(p.get("issue_codes", [])) or "bank issue",
            "claim": p.get("claim_type", ""),
            "stage": STAGE_NAMES.get(p.get("stage", ""), {}).get(language, p.get("stage", "")),
            "waited": duration(float(p.get("days_in_stage", 0) or 0), language),
            "target": duration(float(p.get("sla_days", 0) or 0), language),
            "tier": TIER_NAMES.get(p.get("escalated_to", ""), {}).get(language, p.get("escalated_to", "")),
            "student": student.full_name, "district": student.district,
        }
        body = render(template_key, language, params)
        stored = 0
        for user in await self.recipients(student):
            channels = [NotificationChannel.PUSH] + ([NotificationChannel.SMS] if critical else [])
            for channel in channels:
                result = await self.db.execute(insert(Notification).values(
                    id=new_id(), user_id=user.id,
                    student_id=student.id, event_id=event.event_id, template_key=template_key, channel=channel,
                    language=language, body=body, data={"application_id": params["app_id"], "event_type": event.type},
                ).on_conflict_do_nothing(constraint="uq_notification_once"))
                if result.rowcount:
                    stored += 1
                    if channel == NotificationChannel.SMS:
                        await send_sms(self.db, user.phone, body, f"NOTIFY_{template_key}")
        if event.type == "SLABreached":
            stored += await self._notify_officers(event, student, params)
        await self.db.commit()
        return stored

    async def _notify_officers(self, event: BaseEvent, student: Student, params: dict) -> int:
        """Remind officers of the escalated tier, as ONE digest per officer, stage and day (no alert floods)."""
        from app.dependencies import officer_covers
        role = UserRole(event.payload.get("escalated_to", "INSTITUTE_OFFICER"))
        stage = event.payload.get("stage", "")
        day = event.occurred_at[:10]
        officers = (await self.db.execute(select(User).where(User.role == role, User.is_active.is_(True)))).scalars()
        created = 0
        for officer in officers:
            if not officer_covers(officer, student.state, student.district):
                continue
            digest_id = f"sla-digest:{stage}:{day}"
            existing = (await self.db.execute(select(Notification).where(
                Notification.event_id == digest_id, Notification.user_id == officer.id,
                Notification.channel == NotificationChannel.PUSH))).scalar_one_or_none()
            app_ids = list((existing.data or {}).get("application_ids", [])) if existing else []
            if params["app_id"] in app_ids:
                continue  # this application is already in today's digest
            app_ids.append(params["app_id"])
            p = event.payload
            body = render("SLA_BREACH_OFFICER", "en", {
                **params, "count": len(app_ids),
                "stage": STAGE_NAMES.get(stage, {}).get("en", stage),
                "waited": duration(float(p.get("days_in_stage", 0) or 0), "en"),
                "target": duration(float(p.get("sla_days", 0) or 0), "en")})
            data = {"application_ids": app_ids, "stage": stage, "event_type": event.type}
            if existing is None:
                self.db.add(Notification(user_id=officer.id, student_id=None, event_id=digest_id,
                                         template_key="SLA_BREACH_OFFICER", channel=NotificationChannel.PUSH,
                                         language="en", body=body, data=data))
                created += 1
            else:
                existing.body, existing.data, existing.read_at = body, data, None  # updated digest shows as unread
        return created
