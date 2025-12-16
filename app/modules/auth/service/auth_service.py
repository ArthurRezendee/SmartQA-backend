from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.user.model.user_model import User
from app.core.security import hash_password, verify_password, create_access_token
from app.modules.auth.providers.google import verify_google_token
from app.jobs.user.send_confirmation_email import send_confirmation_email


class AuthService:

    async def register(self, db: AsyncSession, name: str, email: str, password: str):
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("Email já cadastrado")

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password)
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)
        
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

        token = create_access_token({"sub": str(user.id)})
        return user, token

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

        token = create_access_token({"sub": str(user.id)})
        return user, token