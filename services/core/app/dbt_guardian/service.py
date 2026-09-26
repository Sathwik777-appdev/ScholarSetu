import uuid
from .schemas import DBTHealthCheckResult, DBTIssue, DBTFailureGuidance, DBTRetryResult, DBTStatus
from app.shared.types import PaymentState

class DBTGuardianService:
    """Pre-sanction payment health checks and post-failure guidance."""
    
    FAILURE_CODE_MAP = {
        "INACTIVE_ACCOUNT": {
            "message_en": "Your bank account appears inactive. Please do one transaction or visit your bank branch.",
            "message_hi": "आपका बैंक खाता निष्क्रिय लग रहा है। कृपया एक लेनदेन करें या अपनी बैंक शाखा पर जाएं।",
            "fix_steps": ["Visit your nearest bank branch", "Make any transaction (deposit/withdrawal)", "Ask the bank to reactivate your account"]
        },
        "AADHAAR_NOT_SEEDED": {
            "message_en": "Your Aadhaar is not linked to a bank account for government payments. Visit your bank with your Aadhaar card.",
            "message_hi": "आपका आधार सरकारी भुगतान के लिए बैंक खाते से जुड़ा नहीं है। अपना आधार कार्ड लेकर बैंक जाएं।",
            "fix_steps": ["Carry your Aadhaar card to your bank branch", "Ask for NPCI/DBT Aadhaar seeding", "This is different from Aadhaar linking"]
        },
        "NAME_MISMATCH": {
            "message_en": "The name on your bank account differs from your Aadhaar. Ask your bank to correct it.",
            "message_hi": "आपके बैंक खाते पर नाम आपके आधार से अलग है। बैंक से सुधार करवाएं।",
            "fix_steps": ["Check the exact name on your Aadhaar", "Visit your bank with Aadhaar and passbook", "Request name correction to match Aadhaar"]
        },
        "ACCOUNT_BLOCKED": {
            "message_en": "Your bank account appears to be blocked or frozen. Contact your bank immediately.",
            "message_hi": "आपका बैंक खाता अवरुद्ध या फ्रीज लग रहा है। तुरंत अपने बैंक से संपर्क करें।",
            "fix_steps": ["Visit your bank branch with ID proof", "Ask why the account is blocked", "Complete any pending KYC requirements"]
        },
        "INSUFFICIENT_BALANCE_IN_SCHEME": {
            "message_en": "The payment is pending due to a scheme fund issue. This is not your problem — we are following up.",
            "message_hi": "योजना कोष की समस्या के कारण भुगतान लंबित है। यह आपकी समस्या नहीं है — हम अनुवर्ती कार्रवाई कर रहे हैं।",
            "fix_steps": ["No action needed from your side", "The Ministry has been notified", "You will receive an update when resolved"]
        }
    }
    
    async def pre_sanction_check(self, application_id: str) -> DBTHealthCheckResult:
        """Run all pre-sanction checks before payment is initiated."""
        # Mock health check result
        issues = []
        overall_status = "PASS"
        
        # In a real scenario, this would query PFMS/NPCI mappers
        return DBTHealthCheckResult(
            overall_status=overall_status,
            checks=["Aadhaar Seeded", "Account Active", "Name Matched", "Account Type OK"],
            issues=issues
        )
    
    async def handle_payment_failure(self, payment_id: str, failure_code: str) -> DBTFailureGuidance:
        """Translate failure code to plain-language fix-it steps."""
        guidance = self.FAILURE_CODE_MAP.get(failure_code, {
            "message_en": "An unknown error occurred with your payment.",
            "message_hi": "आपके भुगतान में एक अज्ञात त्रुटि हुई।",
            "fix_steps": ["Contact support for assistance"]
        })
        
        retry_id = str(uuid.uuid4())
        
        return DBTFailureGuidance(
            failure_code=failure_code,
            plain_message=guidance["message_en"],
            plain_message_hi=guidance["message_hi"],
            fix_steps=guidance["fix_steps"],
            retry_id=retry_id
        )
    
    async def confirm_fix_and_retry(self, retry_id: str) -> DBTRetryResult:
        """Student confirms they fixed the issue → re-trigger payment."""
        return DBTRetryResult(
            retry_initiated=True,
            message="Your payment retry has been successfully initiated."
        )
    
    async def get_dbt_status(self, application_id: str) -> DBTStatus:
        """Full DBT status for an application."""
        health_check = await self.pre_sanction_check(application_id)
        
        return DBTStatus(
            health_check=health_check,
            payment_state=PaymentState.PENDING,
            retries=[]
        )
