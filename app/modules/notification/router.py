from fastapi import APIRouter, Depends, Query

from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id
from app.modules.notification.controller.notification_controller import NotificationController

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)

controller = NotificationController()


@router.get("/")
async def list_notifications(
    unread_only: bool = Query(False, description="Retornar apenas notificações não lidas"),
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.list_notifications(db, user_id, unread_only)


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.mark_as_read(db, notification_id, user_id)


@router.post("/read-all")
async def mark_all_as_read(
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.mark_all_as_read(db, user_id)


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    await controller.delete_notification(db, notification_id, user_id)
