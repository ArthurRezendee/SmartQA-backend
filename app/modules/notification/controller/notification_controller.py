from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.shared.controller import BaseController
from app.shared.responses import success, error
from app.modules.notification.model.notification_model import Notification
from app.modules.organization.model.organization_invitation_model import OrganizationInvitation


class NotificationController(BaseController):

    async def list_notifications(
        self,
        db: AsyncSession,
        user_id: int,
        unread_only: bool = False,
    ):
        try:
            query = select(Notification).where(Notification.user_id == user_id)
            if unread_only:
                query = query.where(Notification.is_read == False)
            query = query.order_by(Notification.created_at.desc())

            result = await db.execute(query)
            notifications = result.scalars().all()

            # Busca status real dos convites em uma única query
            invite_ids = [
                n.payload["invitation_id"]
                for n in notifications
                if n.type == "organization_invite" and n.payload and n.payload.get("invitation_id")
            ]
            invite_status_map: dict[int, str] = {}
            if invite_ids:
                inv_result = await db.execute(
                    select(OrganizationInvitation.id, OrganizationInvitation.status).where(
                        OrganizationInvitation.id.in_(invite_ids)
                    )
                )
                invite_status_map = {row.id: row.status for row in inv_result.all()}

            data = [
                {
                    "id": n.id,
                    "type": n.type,
                    "title": n.title,
                    "message": n.message,
                    "is_read": n.is_read,
                    "payload": n.payload,
                    "invitation_status": (
                        invite_status_map.get(n.payload["invitation_id"])
                        if n.type == "organization_invite" and n.payload and n.payload.get("invitation_id")
                        else None
                    ),
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                    "updated_at": n.updated_at.isoformat() if n.updated_at else None,
                }
                for n in notifications
            ]

            unread_count = sum(1 for n in notifications if not n.is_read)

            return success(
                "Notificações recuperadas",
                {"notifications": data, "unread_count": unread_count},
            )

        except Exception as e:
            return error(f"Erro ao buscar notificações: {str(e)}")

    async def mark_as_read(self, db: AsyncSession, notification_id: int, user_id: int):
        try:
            result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id,
                    )
                )
            )
            notification = result.scalar_one_or_none()
            if not notification:
                return error("Notificação não encontrada", status_code=404)

            notification.is_read = True
            await db.commit()
            return success("Notificação marcada como lida", None)

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao atualizar notificação: {str(e)}")

    async def mark_all_as_read(self, db: AsyncSession, user_id: int):
        try:
            result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read == False,
                    )
                )
            )
            for notification in result.scalars().all():
                notification.is_read = True
            await db.commit()
            return success("Todas as notificações foram marcadas como lidas", None)

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao atualizar notificações: {str(e)}")

    async def delete_notification(self, db: AsyncSession, notification_id: int, user_id: int):
        try:
            result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.id == notification_id,
                        Notification.user_id == user_id,
                    )
                )
            )
            notification = result.scalar_one_or_none()
            if not notification:
                return error("Notificação não encontrada", status_code=404)

            await db.delete(notification)
            await db.commit()
            return success("Notificação removida", None)

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao remover notificação: {str(e)}")
