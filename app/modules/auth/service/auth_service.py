from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.user.model.user_model import User
from app.core.security import hash_password, verify_password, create_access_token


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
