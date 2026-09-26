from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.gateway.models import User
from app.nudge.models import Notification
from app.nudge.schemas import NotificationOut
from app.shared.types import NotificationChannel

router = APIRouter(prefix="/v1", tags=["Notifications"])


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = False, limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """In-app notifications for the signed-in user, newest first (the app polls this)."""
    query = select(Notification).where(Notification.user_id == user.id,
                                       Notification.channel == NotificationChannel.PUSH)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    rows = (await db.execute(query.order_by(Notification.created_at.desc()).limit(limit))).scalars()
    return [NotificationOut.model_validate(n, from_attributes=True) for n in rows]


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_read(notification_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    notification = await db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read_at = notification.read_at or datetime.now(timezone.utc)
    await db.commit()
    return NotificationOut.model_validate(notification, from_attributes=True)
