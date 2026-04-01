import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.modules.user.model.user_model import User
from app.modules.plans.model.plan_model import Plan
from app.modules.billing.model.billing_account_model import BillingAccount
from app.modules.billing.controller.billing_controller import BillingController
from app.modules.organization.model.organization_invitation_model import OrganizationInvitation
from app.modules.notification.model.notification_model import Notification

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_verification_code,
)
from app.core.config import settings
from app.modules.auth.providers.google import verify_google_token
from app.jobs.user.send_confirmation_email import send_confirmation_email
from app.jobs.user.send_password_reset_email import send_password_reset_email


class AuthService:

    def __init__(self):
        self.billing_controller = BillingController()

    async def _assign_free_plan_if_missing(self, db: AsyncSession, user: User):
        result = await db.execute(
            select(BillingAccount).where(BillingAccount.owner_user_id == user.id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        plan_result = await db.execute(select(Plan).where(Plan.slug == "free"))
        free_plan = plan_result.scalar_one_or_none()

        if not free_plan:
            raise ValueError("Free plan not found")

        return await self.billing_controller.create_billing_account(
            db=db,
            plan_id=free_plan.id,
            user_id=user.id,
        )

    async def _create_pending_invite_notifications(self, db: AsyncSession, user: User):
        """
        Ao criar/logar um usuário, verifica convites pendentes para seu e-mail
        e cria as notificações internas correspondentes.
        """
        from sqlalchemy.orm import selectinload
        from app.modules.organization.model.organization_model import Organization

        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(OrganizationInvitation)
            .where(
                and_(
                    OrganizationInvitation.invited_email == user.email,
                    OrganizationInvitation.status == "pending",
                    OrganizationInvitation.expires_at > now,
                    OrganizationInvitation.user_id == None,
                )
            )
            .options(
                selectinload(OrganizationInvitation.organization),
                selectinload(OrganizationInvitation.invited_by),
            )
        )
        pending_invites = result.scalars().all()

        for inv in pending_invites:
            # vincula o convite ao usuário recém-cadastrado
            inv.user_id = user.id

            org_name = inv.organization.name if inv.organization else "uma organização"
            inviter_name = inv.invited_by.name if inv.invited_by else None

            notification = Notification(
                user_id=user.id,
                type="organization_invite",
                title=f"Convite para {org_name}",
                message=(
                    f"{inviter_name or 'Alguém'} te convidou para participar de "
                    f"{org_name} como {inv.role}."
                ),
                payload={
                    "invitation_id": inv.id,
                    "organization_id": inv.organization_id,
                    "organization_name": org_name,
                    "organization_slug": inv.organization.slug if inv.organization else None,
                    "token": inv.token,
                    "role": inv.role,
                    "inviter_name": inviter_name,
                },
            )
            db.add(notification)

        if pending_invites:
            await db.flush()

    def _set_verification_code(self, user: User) -> str:
        code = generate_verification_code()
        user.email_verification_code = code
        user.email_verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
        return code

    async def register(self, db: AsyncSession, name: str, email: str, password: str):
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("Email já cadastrado")

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            email_verified=False,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        await self._assign_free_plan_if_missing(db, user)
        await self._create_pending_invite_notifications(db, user)

        code = self._set_verification_code(user)
        await db.commit()

        send_confirmation_email.delay(user.name, user.email, code)

        token = create_access_token({"sub": str(user.id)})
        return user, token

    async def login(self, db: AsyncSession, email: str, password: str):
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            raise ValueError("Credenciais inválidas")

        if not verify_password(password, user.password_hash):
            raise ValueError("Credenciais inválidas")

        await self._assign_free_plan_if_missing(db, user)

        token = create_access_token({"sub": str(user.id)})
        return user, token

    async def verify_email_code(self, db: AsyncSession, user_id: int, code: str):
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Usuário não encontrado")

        if user.email_verified:
            raise ValueError("E-mail já confirmado")

        if not user.email_verification_code or not user.email_verification_expires_at:
            raise ValueError("Nenhum código de verificação pendente")

        expires_at = user.email_verification_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            raise ValueError("Código expirado")

        if user.email_verification_code != code:
            raise ValueError("Código inválido")

        user.email_verified = True
        user.email_verification_code = None
        user.email_verification_expires_at = None
        await db.commit()

    async def request_password_reset(self, db: AsyncSession, email: str):
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        # Sempre retorna sucesso para não vazar se o email existe ou não
        if not user:
            return

        token = secrets.token_urlsafe(32)
        user.password_reset_token = token
        user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        await db.commit()

        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        send_password_reset_email.delay(user.name, user.email, reset_url)

    async def reset_password(self, db: AsyncSession, token: str, new_password: str):
        result = await db.execute(
            select(User).where(User.password_reset_token == token)
        )
        user = result.scalar_one_or_none()

        if not user or not user.password_reset_expires_at:
            raise ValueError("Token inválido ou expirado")

        expires_at = user.password_reset_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            raise ValueError("Token inválido ou expirado")

        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        await db.commit()

    async def login_google(self, db: AsyncSession, id_token: str):
        google_user = await verify_google_token(id_token)

        email = google_user["email"]
        google_id = google_user["sub"]
        name = google_user.get("name")
        avatar = google_user.get("picture")

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            if not user.google_id:
                user.google_id = google_id
                user.avatar_url = avatar
                await db.commit()

            if not user.email_verified:
                code = self._set_verification_code(user)
                await db.commit()
                send_confirmation_email.delay(user.name, user.email, code)
        else:
            user = User(
                name=name,
                email=email,
                google_id=google_id,
                avatar_url=avatar,
                is_active=True,
                email_verified=False,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            await self._assign_free_plan_if_missing(db, user)
            await self._create_pending_invite_notifications(db, user)

            code = self._set_verification_code(user)
            await db.commit()

            send_confirmation_email.delay(user.name, user.email, code)

        token = create_access_token({"sub": str(user.id)})
        return user, token
