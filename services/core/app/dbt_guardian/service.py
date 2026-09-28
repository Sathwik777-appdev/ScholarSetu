"""DBT Guardian (ARCHITECTURE.md §6.6): check that a payment will land before sanction, and turn
payment failures into plain-language fix steps. A check never passes when a source is unreachable."""

import logging
from typing import Optional

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dbt_guardian.models import DbtHealthCheck, DbtRetry
from app.dbt_guardian.schemas import (
    DBTCheck, DBTHealthCheckResult, DBTIssue, DBTRetryOut, DBTStatus, PaymentWithGuidance,
)
from app.ledger.models import Application, Payment
from app.ledger.service import LedgerService, money
from app.shared.events import emit
from app.shared.types import PaymentState
from app.students.models import Student
from app.verification.identity_resolver import IndicIdentityResolver
from app.verification.sources import SourceClient, SourceUnavailable, get_source_client

logger = logging.getLogger("scholarsetu.dbt")

GUIDANCE = {
    "AADHAAR_NOT_SEEDED": {
        "en": "Your Aadhaar is not linked to a bank account for government payments.",
        "hi": "आपका आधार सरकारी भुगतान के लिए किसी बैंक खाते से जुड़ा (सीड) नहीं है।",
        "steps_en": ["Go to your bank branch with your Aadhaar card and passbook",
                     "Ask for Aadhaar seeding for DBT (NPCI mapping) on your account",
                     "This is different from only linking Aadhaar to the account; ask specifically for DBT seeding",
                     "Tell us here once the bank confirms, and we will check again"],
        "steps_hi": ["आधार कार्ड और पासबुक लेकर अपनी बैंक शाखा जाएँ",
                     "अपने खाते पर DBT के लिए आधार सीडिंग (NPCI मैपिंग) करवाने को कहें",
                     "यह सिर्फ़ आधार लिंक करने से अलग है; साफ़ तौर पर DBT सीडिंग के लिए कहें",
                     "बैंक पुष्टि कर दे तो यहाँ बताएँ, हम फिर से जाँच करेंगे"],
    },
    "INACTIVE_ACCOUNT": {
        "en": "Your bank account appears inactive (dormant).",
        "hi": "आपका बैंक खाता निष्क्रिय लग रहा है।",
        "steps_en": ["Make one deposit or withdrawal, or visit your branch", "Ask the bank to reactivate the account"],
        "steps_hi": ["एक जमा या निकासी करें, या शाखा जाएँ", "बैंक से खाता फिर से चालू करने को कहें"],
    },
    "ACCOUNT_BLOCKED": {
        "en": "Your bank account appears to be blocked or frozen.",
        "hi": "आपका बैंक खाता बंद या फ्रीज़ लग रहा है।",
        "steps_en": ["Visit your branch with an ID proof", "Complete any pending KYC the bank asks for"],
        "steps_hi": ["पहचान पत्र लेकर शाखा जाएँ", "बैंक जो KYC माँगे, उसे पूरा करें"],
    },
    "NAME_MISMATCH": {
        "en": "The name on your bank account differs from your Aadhaar.",
        "hi": "आपके बैंक खाते का नाम आपके आधार से अलग है।",
        "steps_en": ["Check the exact name on your Aadhaar", "Ask your bank to correct the account name to match Aadhaar"],
        "steps_hi": ["आधार पर लिखा सही नाम देखें", "बैंक से खाते का नाम आधार के अनुसार ठीक करवाएँ"],
    },
    "UNSUITABLE_ACCOUNT_TYPE": {
        "en": "This type of account cannot receive scholarship DBT.",
        "hi": "इस प्रकार के खाते में छात्रवृत्ति DBT नहीं आ सकती।",
        "steps_en": ["Open or use a savings account in your own name", "Seed Aadhaar to that account for DBT"],
        "steps_hi": ["अपने नाम से बचत खाता खोलें या उसका उपयोग करें", "उस खाते पर DBT के लिए आधार सीड करवाएँ"],
    },
    "NO_BANK_ACCOUNT": {
        "en": "No bank account was found for your Aadhaar.",
        "hi": "आपके आधार से कोई बैंक खाता नहीं मिला।",
        "steps_en": ["Open a savings account (a zero-balance BSBD account is enough)", "Seed Aadhaar to it for DBT"],
        "steps_hi": ["बचत खाता खोलें (ज़ीरो बैलेंस BSBD खाता भी चलेगा)", "उस पर DBT के लिए आधार सीड करवाएँ"],
    },
}
UNKNOWN = {"en": "The payment failed for a reason the bank has not explained yet.",
           "hi": "भुगतान विफल हुआ; बैंक ने अभी कारण नहीं बताया है।",
           "steps_en": ["Contact your institute's scholarship nodal officer"],
           "steps_hi": ["अपने संस्थान के छात्रवृत्ति नोडल अधिकारी से संपर्क करें"]}
SUITABLE_ACCOUNT_TYPES = {"SAVINGS", "BSBD", "PMJDY"}


def guidance(code: str) -> DBTIssue:
    g = GUIDANCE.get(code, UNKNOWN)
    return DBTIssue(code=code, message=g["en"], message_hi=g["hi"], fix_steps=g["steps_en"], fix_steps_hi=g["steps_hi"])


class DBTError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def health_result(check: DbtHealthCheck) -> DBTHealthCheckResult:
    return DBTHealthCheckResult(id=check.id, application_id=check.application_id, overall_status=check.status,
                                checks=[DBTCheck(**c) for c in check.checks],
                                issues=[DBTIssue(**i) for i in check.issues],
                                bank_account_masked=check.bank_account_masked, checked_at=check.created_at)


class DBTGuardianService:
    def __init__(self, db: AsyncSession, sources: SourceClient):
        self.db = db
        self.sources = sources
        self.ledger = LedgerService(db)

    async def health_check(self, app: Application, requested_by: str) -> DbtHealthCheck:
        student = await self.db.get(Student, app.student_id)
        checks: list[DBTCheck] = []
        issues: list[DBTIssue] = []
        masked = None
        try:
            if not student.aadhaar_ref_token:
                raise DBTError(422, "The student record has no Aadhaar reference")
            mapper = await self.sources.request("GET", f"/pfms/npci/mapper/{student.aadhaar_ref_token}")
            account = await self.sources.request("POST", "/pfms/dbt/verify-account",
                                                 json={"aadhaar_ref": student.aadhaar_ref_token})
        except SourceUnavailable as exc:
            logger.warning("DBT sources unavailable for %s: %s", app.id, exc)
            checks = [DBTCheck(code="PFMS_NPCI", status="UNAVAILABLE", detail="PFMS/NPCI could not be reached")]
            status = "UNAVAILABLE"
        else:
            if mapper is None or account is None:
                checks.append(DBTCheck(code="BANK_ACCOUNT", status="FAIL", detail="No bank account found"))
                issues.append(guidance("NO_BANK_ACCOUNT"))
            else:
                masked = account.get("account_masked")
                seeded = bool(mapper.get("seeded"))
                checks.append(DBTCheck(code="AADHAAR_SEEDED", status="PASS" if seeded else "FAIL",
                                       detail=f"Aadhaar seeded with {mapper.get('bank_name')}" if seeded
                                       else "Aadhaar is not seeded to any account for DBT (NPCI mapper)"))
                if not seeded:
                    issues.append(guidance("AADHAAR_NOT_SEEDED"))
                active = account.get("account_status") == "ACTIVE"
                checks.append(DBTCheck(code="ACCOUNT_ACTIVE", status="PASS" if active else "FAIL",
                                       detail=f"Account status: {account.get('account_status')}"))
                if not active:
                    issues.append(guidance("INACTIVE_ACCOUNT" if account.get("account_status") == "DORMANT"
                                           else "ACCOUNT_BLOCKED"))
                name = IndicIdentityResolver().compare_names(student.full_name, account.get("account_holder_name", ""))
                name_ok = name.score >= settings.IDENTITY_AUTO_VERIFY_THRESHOLD
                checks.append(DBTCheck(code="NAME_MATCH", status="PASS" if name_ok else "FAIL",
                                       detail=f"Account holder '{account.get('account_holder_name')}' vs "
                                              f"'{student.full_name}': score {name.score:.2f}"))
                if not name_ok:
                    issues.append(guidance("NAME_MISMATCH"))
                type_ok = account.get("account_type") in SUITABLE_ACCOUNT_TYPES
                checks.append(DBTCheck(code="ACCOUNT_TYPE", status="PASS" if type_ok else "FAIL",
                                       detail=f"Account type: {account.get('account_type')}"))
                if not type_ok:
                    issues.append(guidance("UNSUITABLE_ACCOUNT_TYPE"))
            status = "PASS" if checks and all(c.status == "PASS" for c in checks) else "FAIL"

        record = DbtHealthCheck(application_id=app.id, student_id=app.student_id, status=status,
                                checks=[c.model_dump() for c in checks], issues=[i.model_dump() for i in issues],
                                bank_account_masked=masked, requested_by=requested_by)
        self.db.add(record)
        await self.db.flush()
        await emit(self.db, "dbt.health_checked", "DBTHealthChecked",
                   {"application_id": app.id, "student_id": app.student_id, "scheme": app.scheme.value,
                    "status": status, "issue_codes": [i.code for i in issues], "health_check_id": record.id},
                   correlation_id=app.id)
        return record

    async def latest_check(self, app_id: str) -> Optional[DbtHealthCheck]:
        return (await self.db.execute(select(DbtHealthCheck).where(DbtHealthCheck.application_id == app_id)
                                      .order_by(DbtHealthCheck.created_at.desc()).limit(1))).scalar_one_or_none()

    async def status(self, app: Application) -> DBTStatus:
        latest = await self.latest_check(app.id)
        payments = await self.ledger.payments_for([app.id])
        retries = (await self.db.execute(select(DbtRetry).where(DbtRetry.application_id == app.id)
                                         .order_by(DbtRetry.created_at))).scalars()
        return DBTStatus(
            application_id=app.id, latest_health_check=health_result(latest) if latest else None,
            payments=[PaymentWithGuidance(payment_id=p.id, instalment=p.instalment, amount=money(p.amount),
                                          state=p.state, failure_code=p.failure_code,
                                          guidance=guidance(p.failure_code) if p.failure_code else None)
                      for p in payments],
            retries=[DBTRetryOut(id=r.id, payment_id=r.payment_id, status=r.status, pfms_ref=r.pfms_ref,
                                 failure_code=r.failure_code, created_at=r.created_at) for r in retries],
        )

    async def request_retry(self, app: Application, payment_id: str, actor: str) -> DBTRetryOut:
        """The student says the bank problem is fixed: re-check, then re-request the payment from PFMS.

        The payment row is locked for the whole request, so two retries (a double tap, app and SMS) are
        serialised: the second sees the payment is no longer FAILED and is refused. PFMS gets a reference
        unique to this attempt, so resending the same attempt can never create a second transfer."""
        payment = (await self.db.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update())).scalar_one_or_none()
        if payment is None or payment.application_id != app.id:
            raise DBTError(404, "Payment not found")
        await self.db.refresh(payment)  # the state as committed by whoever held the lock before us
        if payment.state != PaymentState.FAILED:
            raise DBTError(409, f"Only failed payments can be retried (this one is {payment.state.value})")
        attempt = 1 + (await self.db.scalar(select(func.count()).select_from(DbtRetry).where(
            DbtRetry.payment_id == payment.id, DbtRetry.status.in_(("SUBMITTED", "CREDITED", "FAILED")))) or 0)
        check = await self.health_check(app, actor)
        retry = DbtRetry(payment_id=payment.id, application_id=app.id, status="BLOCKED",
                         health_check_id=check.id, requested_by=actor)
        self.db.add(retry)
        if check.status != "PASS":
            await self.db.flush()
            return DBTRetryOut(id=retry.id, payment_id=payment.id, status=retry.status, pfms_ref=None,
                               failure_code=None, issues=[DBTIssue(**i) for i in check.issues],
                               created_at=retry.created_at)
        student = await self.db.get(Student, app.student_id)
        try:
            submitted = await self.sources.request("POST", "/pfms/dbt/initiate-payment", json={
                "aadhaar_ref": student.aadhaar_ref_token, "amount": money(payment.amount),
                "reference": f"{payment.id}:retry-{attempt}"})
        except SourceUnavailable:
            raise DBTError(503, "PFMS could not be reached; the retry was not sent. Try again later.")
        retry.status, retry.pfms_ref = "SUBMITTED", submitted["txn_ref"]
        await self.ledger.update_payment(app, payment.id, PaymentState.RETRYING, actor, pfms_ref=submitted["txn_ref"])
        await self.db.flush()
        return DBTRetryOut(id=retry.id, payment_id=payment.id, status=retry.status, pfms_ref=retry.pfms_ref,
                           failure_code=None, created_at=retry.created_at)

    async def settle_retry(self, retry: DbtRetry, actor: str) -> DbtRetry:
        """Ask PFMS how a submitted retry ended and record the outcome in the ledger."""
        result = await self.sources.request("GET", f"/pfms/dbt/status/{retry.pfms_ref}")
        if result is None or result.get("status") not in ("SUCCESS", "FAILED"):
            return retry  # still pending
        app = await self.db.get(Application, retry.application_id)
        if result["status"] == "SUCCESS":
            await self.ledger.update_payment(app, retry.payment_id, PaymentState.CREDITED, actor)
            retry.status = "CREDITED"
        else:
            await self.ledger.update_payment(app, retry.payment_id, PaymentState.FAILED, actor,
                                             failure_code=result.get("failure_code"))
            retry.status, retry.failure_code = "FAILED", result.get("failure_code")
        await self.db.flush()
        return retry


def get_dbt_service(db: AsyncSession = Depends(get_db),
                    sources: SourceClient = Depends(get_source_client)) -> DBTGuardianService:
    return DBTGuardianService(db, sources)
