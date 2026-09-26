from typing import Dict, Any, List
from app.shared.events import BaseEvent
from app.shared.types import NotificationChannel

class NudgeService:
    """Event-driven multi-channel notification engine."""
    
    TEMPLATES = {
        "DEFICIENCY_RAISED": {
            "en": "Action needed: {deficiency_description}. Please respond by {deadline}.",
            "hi": "कार्रवाई आवश्यक: {deficiency_description}। कृपया {deadline} तक जवाब दें।"
        },
        "SANCTIONED": {
            "en": "Great news! Your {scheme_name} scholarship for {academic_year} has been sanctioned. Amount: ₹{amount}.",
            "hi": "शुभ समाचार! आपकी {scheme_name} छात्रवृत्ति {academic_year} के लिए स्वीकृत हो गई है। राशि: ₹{amount}।"
        },
        "CREDITED": {
            "en": "₹{amount} has been credited to your bank account for {scheme_name} ({instalment_desc}).",
            "hi": "₹{amount} आपके बैंक खाते में {scheme_name} ({instalment_desc}) के लिए जमा हो गया है।"
        },
        "PAYMENT_FAILED": {
            "en": "Payment failed for {scheme_name}. Reason: {reason}. {fix_steps}",
            "hi": "{scheme_name} का भुगतान विफल रहा। कारण: {reason}। {fix_steps}"
        },
        "RENEWAL_DUE": {
            "en": "Your {scheme_name} scholarship renewal is due. Apply before {deadline}.",
            "hi": "आपकी {scheme_name} छात्रवृत्ति का नवीनीकरण बकाया है। {deadline} से पहले आवेदन करें।"
        },
        "TRANSITION_DETECTED": {
            "en": "Congratulations! You may be eligible for {next_scheme}. We've pre-filled your application.",
            "hi": "बधाई! आप {next_scheme} के लिए पात्र हो सकते हैं। हमने आपका आवेदन पहले से भर दिया है।"
        },
        "ATTESTATION_EXPIRING": {
            "en": "Your {claim_type} attestation expires on {expiry_date}. Renew now to avoid delays.",
            "hi": "आपका {claim_type} प्रमाणन {expiry_date} को समाप्त हो रहा है। विलंब से बचने के लिए अभी नवीनीकरण करें।"
        },
        "SLA_REMINDER_OFFICER": {
            "en": "[Reminder] {count} applications pending your verification for over {days} days.",
            "hi": "[अनुस्मारक] {count} आवेदन {days} दिनों से अधिक समय से आपके सत्यापन हेतु लंबित हैं।"
        },
        "INSTITUTE_VERIFIED": {
            "en": "Your application has been verified by your institute and forwarded for further processing.",
            "hi": "आपका आवेदन आपके संस्थान द्वारा सत्यापित कर दिया गया है और आगे की कार्रवाई के लिए भेज दिया गया है।"
        }
    }
    
    async def handle_event(self, event: BaseEvent) -> None:
        """Process a ledger event and send appropriate notifications."""
        # Dispatch logic based on event type
        pass
    
    async def send_notification(self, user_id: str, template_key: str, params: Dict[str, Any], channels: List[NotificationChannel], language: str = 'hi') -> None:
        """Send a notification through specified channels."""
        template = self.TEMPLATES.get(template_key)
        if not template:
            return
            
        message = template.get(language, template.get("en", "")).format(**params)
        
        for channel in channels:
            if channel == NotificationChannel.SMS:
                await self.send_sms("1234567890", message) # mock phone
            elif channel == NotificationChannel.PUSH:
                await self.send_push(user_id, "Notification", message)
            
    async def send_sms(self, phone: str, message: str) -> None:
        """Send SMS (mock in dev)."""
        print(f"SMS to {phone}: {message}")
    
    async def send_push(self, user_id: str, title: str, body: str) -> None:
        """Send push notification (mock in dev)."""
        print(f"Push to {user_id} - {title}: {body}")
    
    async def escalate(self, application_id: str, current_stage: str, days_stuck: int) -> None:
        """SLA escalation: institute → district → state."""
        print(f"Escalating application {application_id} stuck at {current_stage} for {days_stuck} days.")
