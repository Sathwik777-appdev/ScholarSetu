"""Feature-phone channels (ARCHITECTURE.md §6.1): SMS STATUS command, SMS dev outbox, IVR (not built)."""

import hmac
import html
import re
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import require_role
from app.gateway.models import OutboundSms, User
from app.gateway.service import record_audit, send_sms
from app.jago_skill.templates import NEXT_STEP, scheme_name, status_name
from app.ledger.models import Application
from app.shared.types import UserRole
from app.students.models import Student

router = APIRouter(prefix="/v1", tags=["SMS & IVR"])

STATUS_COMMAND = re.compile(r"^\s*STATUS\s+(APP-[A-Z]+-\d{4}-\d{6})\s*$", re.I)
HELP_TEXT = {"en": "Send STATUS <application id>, e.g. STATUS APP-PM-2026-000002",
             "hi": "STATUS <आवेदन संख्या> भेजें, जैसे STATUS APP-PM-2026-000002"}


class InboundSms(BaseModel):
    model_config = {"extra": "forbid"}
    from_phone: str = Field(..., pattern=r"^[0-9]{10}$")
    body: str = Field(..., max_length=160)


def _gateway_authorised(token: Optional[str]) -> None:
    if not settings.SMS_GATEWAY_TOKEN:
        raise HTTPException(status_code=503, detail="Inbound SMS is not configured")
    if not token or not hmac.compare_digest(token.encode(), settings.SMS_GATEWAY_TOKEN.encode()):
        raise HTTPException(status_code=401, detail="Invalid gateway token")


@router.post("/sms/inbound")
async def inbound_sms(msg: InboundSms, x_sms_gateway_token: Optional[str] = Header(None),
                      db: AsyncSession = Depends(get_db)):
    """Webhook from the SMS gateway. Only a registered student (or their guardian) may ask about an application."""
    _gateway_authorised(x_sms_gateway_token)
    sender = (await db.execute(select(User).where(User.phone == msg.from_phone, User.is_active.is_(True),
                                                  User.role.in_([UserRole.STUDENT, UserRole.GUARDIAN])))).scalar_one_or_none()
    if sender is None:
        await record_audit(db, "SMS_INBOUND_REJECTED", details={"reason": "unregistered number"})
        await db.commit()
        raise HTTPException(status_code=403, detail="Number not registered")

    match = STATUS_COMMAND.match(msg.body)
    lang = "hi"
    if sender.student_id:
        student = await db.get(Student, sender.student_id)
        lang = student.preferred_language if student and student.preferred_language in ("hi", "en") else "hi"
    if not match:
        reply = HELP_TEXT[lang]
    else:
        app = await db.get(Application, match.group(1).upper())
        student = await db.get(Student, app.student_id) if app else None
        owns = app is not None and (app.student_id == sender.student_id or
                                    (sender.role == UserRole.GUARDIAN and student and student.household_id == sender.household_id))
        if not owns:
            reply = {"en": "No application with that number is linked to this phone.",
                     "hi": "इस नंबर से ऐसा कोई आवेदन जुड़ा नहीं है।"}[lang]
        else:
            state = app.canonical_state.value
            reply = (f"{app.id} {scheme_name(app.scheme.value, lang)}: {status_name(state, lang)}. "
                     f"{NEXT_STEP.get(state, {}).get(lang, '')}")[:320]
    await send_sms(db, msg.from_phone, reply, "SMS_STATUS_REPLY")
    await record_audit(db, "SMS_INBOUND", actor=sender, student_id=sender.student_id,
                       details={"command": "STATUS" if match else "HELP"})
    await db.commit()
    return {"status": "replied"}


@router.post("/ivr/call", status_code=501)
async def ivr_call():
    """Missed-call IVR is not built in this prototype (see ARCHITECTURE.md §19)."""
    raise HTTPException(status_code=501, detail="IVR is not implemented")


def _demo_phones():
    return select(User.phone).where(User.is_demo.is_(True))


@router.get("/dev/sms-outbox", response_class=HTMLResponse, include_in_schema=False)
async def sms_outbox(db: AsyncSession = Depends(get_db)):
    """DEMO_MODE only: what the simulated SMS gateway 'sent' to the seeded demo accounts, for running the demo.

    Public, so it shows only messages to demo accounts (which sign in with the published demo code anyway).
    Messages to anyone else, such as a real person's registration or login code, are never shown here; the
    Ministry can read them through the authenticated /v1/dev/sms-outbox/all."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    rows = (await db.execute(select(OutboundSms).where(OutboundSms.to_phone.in_(_demo_phones()))
                             .order_by(OutboundSms.created_at.desc()).limit(100))).scalars()
    body = "".join(f"<tr><td>{r.created_at:%H:%M:%S}</td><td>{html.escape(r.to_phone)}</td>"
                   f"<td>{html.escape(r.category)}</td><td>{html.escape(r.body)}</td></tr>" for r in rows)
    return (f"<!doctype html><meta charset=utf-8><title>SMS outbox (demo)</title><meta http-equiv=refresh content=5>"
            f"<style>body{{font:14px system-ui;margin:24px}}td,th{{padding:6px 10px;border-bottom:1px solid #ddd;"
            f"text-align:left}}</style><h1>Simulated SMS outbox</h1><p>DEMO_MODE only. Messages to the seeded demo accounts; refreshes every 5 "
            f"seconds.</p>"
            f"<table><tr><th>Time</th><th>To</th><th>Type</th><th>Message</th></tr>{body}</table>")


class SimulatedSms(BaseModel):
    created_at: str
    to_phone: str
    category: str
    body: str


@router.get("/dev/sms-outbox/all", response_model=list[SimulatedSms])
async def sms_outbox_all(user: User = Depends(require_role(UserRole.MINISTRY)), db: AsyncSession = Depends(get_db)):
    """DEMO_MODE only, Ministry only: every simulated SMS, so a presenter can show self-registration.
    Each read is audited."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    rows = (await db.execute(select(OutboundSms).order_by(OutboundSms.created_at.desc()).limit(100))).scalars().all()
    await record_audit(db, "DEMO_SMS_OUTBOX_READ", actor=user, details={"messages": len(rows)})
    await db.commit()
    return [SimulatedSms(created_at=r.created_at.isoformat(), to_phone=r.to_phone, category=r.category, body=r.body)
            for r in rows]
