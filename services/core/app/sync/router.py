"""Offline sync for the mobile app (ARCHITECTURE.md §6.1, §8): delta events by cursor, and an idempotent outbox."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import _resolve_student_principal, get_current_user
from app.gateway.models import User
from app.ledger.models import Application, LedgerEvent
from app.ledger.schemas import ApplicationCreate, DeficiencyResponse, LedgerEventOut
from app.ledger.service import LedgerService
from app.shared.types import MitraScope, UserRole
from app.students.models import Student
from .models import SyncReceipt
from .schemas import ItemStatus, OutboxAction, OutboxBatch, OutboxItem, OutboxItemResult, OutboxResponse, SyncPage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/sync", tags=["Offline sync"])


async def _students_in_scope(request: Request, user: User, db: AsyncSession, x_mitra_session: Optional[str]) -> list[str]:
    """The students whose records this device may cache: yourself, your household's children, or the Mitra session's student."""
    if user.role == UserRole.GUARDIAN:
        if not user.household_id:
            return []
        return list((await db.execute(select(Student.id).where(Student.household_id == user.household_id))).scalars())
    principal = await _resolve_student_principal(request, user, db, x_mitra_session, (MitraScope.VIEW_STATUS,))
    return [principal.student_id]


@router.get("", response_model=SyncPage)
async def pull(request: Request, cursor: int = Query(0, ge=0), limit: int = Query(200, ge=1, le=500),
               user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
               x_mitra_session: Optional[str] = Header(None)):
    """Ledger events after `cursor` for the caller's students, oldest first.

    Events younger than SYNC_SETTLE_SECONDS are held back, so an event whose transaction commits after a
    later-numbered one is never skipped by a cursor that has already moved past it."""
    students = await _students_in_scope(request, user, db, x_mitra_session)
    now = datetime.now(timezone.utc)
    events = []
    if students:
        settled = now - timedelta(seconds=settings.SYNC_SETTLE_SECONDS)
        events = list((await db.execute(
            select(LedgerEvent).where(LedgerEvent.student_id.in_(students), LedgerEvent.position > cursor,
                                      LedgerEvent.recorded_at <= settled)
            .order_by(LedgerEvent.position).limit(limit + 1))).scalars())
    has_more = len(events) > limit
    events = events[:limit]
    app_ids = sorted({e.application_id for e in events})
    apps = list((await db.execute(select(Application).where(Application.id.in_(app_ids))))) if app_ids else []
    from app.ledger.router import _app_out
    return SyncPage(events=[LedgerEventOut.model_validate(e, from_attributes=True) for e in events],
                    applications=[_app_out(row[0]) for row in apps],
                    next_cursor=events[-1].position if events else cursor, has_more=has_more, server_time=now)


# ── outbox ───────────────────────────────────────────────────────────────────

MITRA_SCOPES = {
    OutboxAction.CREATE_APPLICATION: (),  # students apply for themselves
    OutboxAction.SUBMIT_APPLICATION: (),
    OutboxAction.RESPOND_DEFICIENCY: (MitraScope.RESPOND_DEFICIENCY,),
}


async def _principal(item: OutboxItem, request: Request, user: User, db: AsyncSession,
                     x_mitra_session: Optional[str]):
    if item.action == OutboxAction.MARK_NOTIFICATION_READ:
        return None
    # Resolved before the receipt is added: a Mitra action's audit record commits on its own.
    return await _resolve_student_principal(request, user, db, x_mitra_session, MITRA_SCOPES[item.action])


async def _apply(item: OutboxItem, principal, user: User, db: AsyncSession) -> dict:
    """Run one action through the same handler the online API uses, so every check applies unchanged."""
    from app.ledger import router as ledger_routes
    from app.nudge.router import mark_read
    p = item.payload
    if item.action == OutboxAction.MARK_NOTIFICATION_READ:
        return (await mark_read(str(p.get("notification_id", "")), user, db)).model_dump(mode="json")
    ledger = LedgerService(db)
    if item.action == OutboxAction.CREATE_APPLICATION:
        out = await ledger_routes.create_application(ApplicationCreate(**p), principal, ledger)
    elif item.action == OutboxAction.SUBMIT_APPLICATION:
        out = await ledger_routes.submit_draft(str(p.get("application_id", "")), principal, ledger)
    else:
        body = DeficiencyResponse(**{k: v for k, v in p.items() if k not in ("application_id", "deficiency_id")})
        out = await ledger_routes.respond_to_deficiency(str(p.get("application_id", "")),
                                                        str(p.get("deficiency_id", "")), body, principal, ledger)
    return out.model_dump(mode="json")


def _from_receipt(item: OutboxItem, receipt: SyncReceipt) -> OutboxItemResult:
    return OutboxItemResult(idempotency_key=item.idempotency_key, action=item.action, status=ItemStatus.DUPLICATE,
                            original_status=ItemStatus(receipt.status), http_status=receipt.http_status,
                            result=receipt.result, error=receipt.error)


async def _receipt(db: AsyncSession, user_id: str, key: str) -> Optional[SyncReceipt]:
    return (await db.execute(select(SyncReceipt).where(SyncReceipt.user_id == user_id,
                                                       SyncReceipt.idempotency_key == key))).scalar_one_or_none()


def _result(item: OutboxItem, status: ItemStatus, code: int, result=None, error=None) -> OutboxItemResult:
    return OutboxItemResult(idempotency_key=item.idempotency_key, action=item.action, status=status,
                            http_status=code, result=result, error=error)


@router.post("/outbox", response_model=OutboxResponse)
async def push(batch: OutboxBatch, request: Request, user: User = Depends(get_current_user),
               db: AsyncSession = Depends(get_db), x_mitra_session: Optional[str] = Header(None)):
    """Apply actions queued while offline, in order. Each item succeeds or fails on its own; resending an
    item with the same idempotency key never applies it twice and returns the original outcome."""
    user_id = user.id
    results = []
    for item in batch.items:
        existing = await _receipt(db, user_id, item.idempotency_key)
        if existing is not None:
            results.append(_from_receipt(item, existing))
            continue
        try:
            principal = await _principal(item, request, user, db, x_mitra_session)
            # The receipt joins the action's own transaction: both commit, or neither does.
            receipt = SyncReceipt(user_id=user_id, idempotency_key=item.idempotency_key, action=item.action.value,
                                  status=ItemStatus.APPLIED.value, http_status=200)
            db.add(receipt)
            result = await _apply(item, principal, user, db)
            receipt.result = result
            await db.commit()
            results.append(_result(item, ItemStatus.APPLIED, 200, result=result))
            continue
        except (HTTPException, ValidationError) as exc:
            await db.rollback()
            code = exc.status_code if isinstance(exc, HTTPException) else 422
            error = exc.detail if isinstance(exc, HTTPException) else exc.errors(include_url=False, include_input=False)
        except IntegrityError:
            await db.rollback()  # the same key arrived concurrently from another request
            code, error = 409, "Conflicting change; try again"
        except Exception:
            await db.rollback()
            logger.exception("outbox item %s (%s) failed", item.idempotency_key, item.action.value)
            code, error = 500, "Temporary server error"
        user = await db.get(User, user_id)  # everything is expired after a rollback
        existing = await _receipt(db, user_id, item.idempotency_key)
        if existing is not None:
            results.append(_from_receipt(item, existing))
        elif code >= 500 or code == 409 and error == "Conflicting change; try again":
            results.append(_result(item, ItemStatus.RETRY, code, error=error))
        else:
            db.add(SyncReceipt(user_id=user_id, idempotency_key=item.idempotency_key, action=item.action.value,
                               status=ItemStatus.REJECTED.value, http_status=code, error=error))
            await db.commit()
            results.append(_result(item, ItemStatus.REJECTED, code, error=error))
    return OutboxResponse(results=results)
