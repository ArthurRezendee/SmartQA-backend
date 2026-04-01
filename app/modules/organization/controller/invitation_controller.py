import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.shared.controller import BaseController
from app.shared.responses import success, error
from app.modules.organization.model.organization_model import Organization
from app.modules.organization.model.organization_member_model import OrganizationMember
from app.modules.organization.model.organization_invitation_model import OrganizationInvitation
from app.modules.notification.model.notification_model import Notification
from app.modules.user.model.user_model import User
from app.modules.billing.model.billing_account_model import BillingAccount
from app.core.config import settings
from app.jobs.organization.send_invitation_email import send_invitation_email


class InvitationController(BaseController):

    # ─── Enviar convite ───────────────────────────────────────────────────────

    async def invite(
        self,
        db: AsyncSession,
        slug: str,
        invited_email: str,
        role: str,
        inviter_user_id: int,
    ):
        try:
            result = await db.execute(
                select(Organization)
                .where(and_(Organization.slug == slug, Organization.is_active == True))
                .options(
                    selectinload(Organization.members),
                    selectinload(Organization.billing_account).selectinload(BillingAccount.plan),
                )
            )
            org = result.scalar_one_or_none()
            if not org:
                return error("Organização não encontrada", status_code=404)

            # verifica permissão do solicitante
            requester = next((m for m in org.members if m.user_id == inviter_user_id), None)
            if not requester or requester.role not in ("owner", "admin"):
                return error("Sem permissão para convidar membros", status_code=403)

            # verifica se o convidado já é membro
            invited_user_result = await db.execute(
                select(User).where(User.email == invited_email)
            )
            invited_user = invited_user_result.scalar_one_or_none()

            if invited_user:
                already_member = next((m for m in org.members if m.user_id == invited_user.id), None)
                if already_member:
                    return error("Usuário já é membro desta organização")

            # verifica se já existe convite pendente para este e-mail
            existing_result = await db.execute(
                select(OrganizationInvitation).where(
                    and_(
                        OrganizationInvitation.organization_id == org.id,
                        OrganizationInvitation.invited_email == invited_email,
                        OrganizationInvitation.status == "pending",
                    )
                )
            )
            if existing_result.scalar_one_or_none():
                return error("Já existe um convite pendente para este e-mail")

            # verifica limite de membros do plano (membros atuais + convites pendentes)
            billing = org.billing_account
            if billing and billing.plan:
                pending_result = await db.execute(
                    select(OrganizationInvitation).where(
                        and_(
                            OrganizationInvitation.organization_id == org.id,
                            OrganizationInvitation.status == "pending",
                        )
                    )
                )
                pending_count = len(pending_result.scalars().all())
                total = len(org.members) + pending_count
                if total >= billing.plan.max_users:
                    return error(
                        f"Limite de {billing.plan.max_users} membros atingido no plano {billing.plan.name}"
                    )

            # busca dados do convidador
            inviter_result = await db.execute(select(User).where(User.id == inviter_user_id))
            inviter = inviter_result.scalar_one_or_none()

            # cria convite
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)

            invitation = OrganizationInvitation(
                organization_id=org.id,
                invited_email=invited_email,
                invited_by_id=inviter_user_id,
                role=role,
                token=token,
                expires_at=expires_at,
                user_id=invited_user.id if invited_user else None,
            )
            db.add(invitation)
            await db.flush()

            # se o usuário já tem conta → cria notificação interna
            if invited_user:
                notification = Notification(
                    user_id=invited_user.id,
                    type="organization_invite",
                    title=f"Convite para {org.name}",
                    message=(
                        f"{inviter.name if inviter else 'Alguém'} te convidou para participar de "
                        f"{org.name} como {role}."
                    ),
                    payload={
                        "invitation_id": invitation.id,
                        "organization_id": org.id,
                        "organization_name": org.name,
                        "organization_slug": org.slug,
                        "token": token,
                        "role": role,
                        "inviter_name": inviter.name if inviter else None,
                        "status": "pending",
                    },
                )
                db.add(notification)

            await db.commit()

            # envia e-mail de convite via Celery
            invite_url = f"{settings.FRONTEND_URL}/invites/{token}"
            send_invitation_email.delay(
                inviter_name=inviter.name if inviter else "Alguém",
                org_name=org.name,
                invited_email=invited_email,
                invite_url=invite_url,
                role=role,
            )

            return success(
                "Convite enviado com sucesso",
                {
                    "invitation_id": invitation.id,
                    "invited_email": invited_email,
                    "role": role,
                    "expires_at": expires_at.isoformat(),
                },
                status_code=201,
            )

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao enviar convite: {str(e)}")

    # ─── Informações públicas do convite ──────────────────────────────────────

    async def get_invitation_info(self, db: AsyncSession, token: str):
        """Endpoint público — retorna dados do convite para exibição no front."""
        try:
            result = await db.execute(
                select(OrganizationInvitation)
                .where(OrganizationInvitation.token == token)
                .options(
                    selectinload(OrganizationInvitation.organization),
                    selectinload(OrganizationInvitation.invited_by),
                )
            )
            invitation = result.scalar_one_or_none()
            if not invitation:
                return error("Convite não encontrado", status_code=404)

            # verifica expiração
            expires_at = invitation.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) > expires_at and invitation.status == "pending":
                invitation.status = "expired"
                await db.commit()

            return success(
                "Convite encontrado",
                {
                    "invitation_id": invitation.id,
                    "status": invitation.status,
                    "organization_name": invitation.organization.name,
                    "organization_slug": invitation.organization.slug,
                    "organization_avatar_color": invitation.organization.avatar_color,
                    "invited_by_name": invitation.invited_by.name,
                    "role": invitation.role,
                    "expires_at": invitation.expires_at.isoformat(),
                    "invited_email": invitation.invited_email,
                },
            )

        except Exception as e:
            return error(f"Erro ao buscar convite: {str(e)}")

    # ─── Aceitar ou recusar convite ───────────────────────────────────────────

    async def respond_to_invitation(
        self,
        db: AsyncSession,
        token: str,
        action: str,
        user_id: int,
    ):
        """
        Requer autenticação.
        action: "accept" | "decline"
        """
        try:
            user_result = await db.execute(select(User).where(User.id == user_id))
            current_user = user_result.scalar_one_or_none()
            if not current_user:
                return error("Usuário não encontrado", status_code=404)

            result = await db.execute(
                select(OrganizationInvitation)
                .where(OrganizationInvitation.token == token)
                .options(
                    selectinload(OrganizationInvitation.organization).selectinload(
                        Organization.members
                    ),
                    selectinload(OrganizationInvitation.organization)
                    .selectinload(Organization.billing_account)
                    .selectinload(BillingAccount.plan),
                )
            )
            invitation = result.scalar_one_or_none()
            if not invitation:
                return error("Convite não encontrado", status_code=404)

            # valida que o convite é para este usuário
            if invitation.invited_email.lower() != current_user.email.lower():
                return error("Este convite não pertence à sua conta", status_code=403)

            if invitation.status != "pending":
                return error(f"Este convite já foi {invitation.status}")

            expires_at = invitation.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                invitation.status = "expired"
                await db.commit()
                return error("Convite expirado", status_code=410)

            if action == "accept":
                org = invitation.organization

                # verifica se já é membro (por algum motivo)
                already = next((m for m in org.members if m.user_id == user_id), None)
                if not already:
                    billing = org.billing_account
                    if billing and billing.plan and len(org.members) >= billing.plan.max_users:
                        return error(
                            f"A organização atingiu o limite de {billing.plan.max_users} membros"
                        )

                    member = OrganizationMember(
                        organization_id=org.id,
                        user_id=user_id,
                        role=invitation.role,
                        invited_by_id=invitation.invited_by_id,
                        accepted_at=datetime.utcnow(),
                    )
                    db.add(member)

                invitation.status = "accepted"
                invitation.user_id = user_id

            elif action == "decline":
                invitation.status = "declined"
                invitation.user_id = user_id

            else:
                return error("Ação inválida. Use 'accept' ou 'decline'")

            # atualiza notificação relacionada com o novo status
            notif_result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.type == "organization_invite",
                    )
                )
            )
            org_name = invitation.organization.name
            for notif in notif_result.scalars().all():
                if notif.payload and notif.payload.get("invitation_id") == invitation.id:
                    notif.is_read = True
                    if action == "accept":
                        notif.title = f"Convite aceito — {org_name}"
                        notif.message = f"Você aceitou o convite para participar de {org_name} como {invitation.role}."
                    else:
                        notif.title = f"Convite recusado — {org_name}"
                        notif.message = f"Você recusou o convite para participar de {org_name}."
                    notif.payload = {**notif.payload, "status": invitation.status}

            await db.commit()

            msg = "Convite aceito com sucesso!" if action == "accept" else "Convite recusado."
            return success(msg, {"status": invitation.status})

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao responder convite: {str(e)}")

    # ─── Listar convites de uma org ───────────────────────────────────────────

    async def list_org_invitations(self, db: AsyncSession, slug: str, user_id: int):
        try:
            result = await db.execute(
                select(Organization)
                .where(and_(Organization.slug == slug, Organization.is_active == True))
                .options(selectinload(Organization.members))
            )
            org = result.scalar_one_or_none()
            if not org:
                return error("Organização não encontrada", status_code=404)

            requester = next((m for m in org.members if m.user_id == user_id), None)
            if not requester or requester.role not in ("owner", "admin"):
                return error("Sem permissão para visualizar convites", status_code=403)

            invitations_result = await db.execute(
                select(OrganizationInvitation)
                .where(OrganizationInvitation.organization_id == org.id)
                .options(selectinload(OrganizationInvitation.invited_by))
                .order_by(OrganizationInvitation.created_at.desc())
            )
            invitations = invitations_result.scalars().all()

            data = [
                {
                    "id": inv.id,
                    "invited_email": inv.invited_email,
                    "role": inv.role,
                    "status": inv.status,
                    "invited_by_name": inv.invited_by.name if inv.invited_by else None,
                    "expires_at": inv.expires_at.isoformat(),
                    "created_at": inv.created_at.isoformat() if inv.created_at else None,
                }
                for inv in invitations
            ]

            return success("Convites listados", data)

        except Exception as e:
            return error(f"Erro ao listar convites: {str(e)}")

    # ─── Cancelar convite ─────────────────────────────────────────────────────

    async def cancel_invitation(self, db: AsyncSession, invitation_id: int, user_id: int):
        try:
            result = await db.execute(
                select(OrganizationInvitation)
                .where(OrganizationInvitation.id == invitation_id)
                .options(
                    selectinload(OrganizationInvitation.organization).selectinload(
                        Organization.members
                    )
                )
            )
            invitation = result.scalar_one_or_none()
            if not invitation:
                return error("Convite não encontrado", status_code=404)

            org = invitation.organization
            requester = next((m for m in org.members if m.user_id == user_id), None)
            if not requester or requester.role not in ("owner", "admin"):
                return error("Sem permissão para cancelar convites", status_code=403)

            if invitation.status != "pending":
                return error("Apenas convites pendentes podem ser cancelados")

            invitation.status = "expired"

            # atualiza notificação do usuário convidado, se existir
            if invitation.user_id:
                notif_result = await db.execute(
                    select(Notification).where(
                        and_(
                            Notification.user_id == invitation.user_id,
                            Notification.type == "organization_invite",
                        )
                    )
                )
                for notif in notif_result.scalars().all():
                    if notif.payload and notif.payload.get("invitation_id") == invitation.id:
                        notif.title = f"Convite cancelado — {org.name}"
                        notif.message = f"O convite para participar de {org.name} foi cancelado pelo administrador."
                        notif.payload = {**notif.payload, "status": "expired"}

            await db.commit()

            return success("Convite cancelado", None)

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao cancelar convite: {str(e)}")
