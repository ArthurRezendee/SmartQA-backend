
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.user.model.user_model import User


class UserService:

    async def list(self, db: AsyncSession):
        result = await db.execute(select(User))
        return result.scalars().all()

    async def get(self, db: AsyncSession, entity_id: int):
        result = await db.execute(
            select(User).where(User.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict):
        record = User(**data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def update(self, db: AsyncSession, entity_id: int, data: dict):
        record = await self.get(db, entity_id)
        if not record:
            return None

        for key, value in data.items():
            setattr(record, key, value)

        await db.commit()
        await db.refresh(record)
        return record

    async def delete(self, db: AsyncSession, entity_id: int):
        record = await self.get(db, entity_id)
        if not record:
            return None

        await db.delete(record)
        await db.commit()
        return record
