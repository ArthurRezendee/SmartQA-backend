from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.user.model.user_model import User
from app.modules.plans.model.plan_model import Plan
from app.modules.billing.model.billing_account_model import BillingAccount
from app.modules.billing.controller.billing_controller import BillingController

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_email_confirmation_token,
)
from app.modules.auth.providers.google import verify_google_token
from app.jobs.user.send_confirmation_email import send_confirmation_email
import jwt


class AuthService:

    def __init__(self):
        self.billing_controller = BillingController()

    async def _assign_free_plan_if_missing(self, db: AsyncSession, user: User):
        """
        Verifica se o usuário já possui billing account.
        Se não possuir, cria automaticamente com o plano 'free'.
        """

        # 🔎 Verifica se já existe billing account
        result = await db.execute(
            select(BillingAccount).where(
                BillingAccount.owner_user_id == user.id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # 🔎 Busca plano free pelo slug
        plan_result = await db.execute(
            select(Plan).where(Plan.slug == "free")
        )
        free_plan = plan_result.scalar_one_or_none()

        if not free_plan:
            raise ValueError("Free plan not found")

        return await self.billing_controller.create_billing_account(
            db=db,
            plan_id=free_plan.id,
            user_id=user.id,
        )

    async def register(self, db: AsyncSession, name: str, email: str, password: str):
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("Email já cadastrado")

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            is_active=True
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        await self._assign_free_plan_if_missing(db, user)

        send_confirmation_email.delay(user.id)

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

    async def confirm_email(self, db: AsyncSession, token: str):
        try:
            user_id = verify_email_confirmation_token(token)
        except jwt.InvalidTokenError:
            raise ValueError("Token inválido ou expirado")

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Usuário não encontrado")

        if user.email_verified:
            raise ValueError("E-mail já confirmado")

        user.email_verified = True
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
                user.email_verified = True
                await db.commit()
        else:
            user = User(
                name=name,
                email=email,
                google_id=google_id,
                avatar_url=avatar,
                email_verified=True,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        await self._assign_free_plan_if_missing(db, user)

        token = create_access_token({"sub": str(user.id)})
        return user, token