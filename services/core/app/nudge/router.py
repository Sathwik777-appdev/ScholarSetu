from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.dependencies import get_current_user, require_role
from app.gateway.models import User
from app.shared.types import UserRole
from .schemas import NotificationRequest, NotificationResponse
from .service import NudgeService

router = APIRouter(prefix="/v1", tags=["Nudge Engine"])


def get_nudge_service() -> NudgeService:
    return NudgeService()


@router.get("/notifications")
async def get_notifications(user: User = Depends(get_current_user)):
    """Notifications for the authenticated user. TODO(Phase 8): read from the notifications table."""
    raise HTTPException(status_code=501, detail="Notifications are not implemented yet")


@router.post("/notifications/test", response_model=NotificationResponse)
async def test_notification(request: NotificationRequest,
                            user: User = Depends(require_role(UserRole.MINISTRY)),
                            service: NudgeService = Depends(get_nudge_service)):
    """Dev-only: render and dispatch a template. Disabled unless DEMO_MODE=true."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    await service.send_notification(
        user_id=request.user_id,
        template_key=request.template_key,
        params=request.params,
        channels=request.channels,
        language=request.language
    )
    return NotificationResponse(status="success", message="Notification triggered successfully")
