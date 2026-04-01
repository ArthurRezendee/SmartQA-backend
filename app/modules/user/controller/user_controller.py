import os
import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.controller import BaseController
from app.shared.responses import success, error
from app.modules.user.service.user_service import UserService
from app.modules.user.model.user_model import User

AVATAR_BASE_DIR = "/dados/user"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_MB = 5


class UserController(BaseController):

    def __init__(self):
        self.service = UserService()

    async def index(self):
        return {
            "status": True,
            "message": "User module ready",
            "data": None
        }

    async def list_users(self, db):
        return await self.service.list(db)

    async def get_user(self, db, entity_id: int):
        return await self.service.get(db, entity_id)

    async def create_user(self, db, data):
        return await self.service.create(db, data.dict())

    async def update_user(self, db, entity_id: int, data):
        return await self.service.update(db, entity_id, data.dict())

    async def delete_user(self, db, entity_id: int):
        return await self.service.delete(db, entity_id)

    async def update_avatar(self, db: AsyncSession, user_id: int, file: UploadFile):
        try:
            if file.content_type not in ALLOWED_TYPES:
                return error("Formato inválido. Use JPEG, PNG ou WebP.")

            contents = await file.read()
            if len(contents) > MAX_SIZE_MB * 1024 * 1024:
                return error(f"Arquivo muito grande. Máximo {MAX_SIZE_MB}MB.")

            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return error("Usuário não encontrado", status_code=404)

            # Remove avatar anterior se existir
            if user.avatar_url:
                old_filepath = user.avatar_url if user.avatar_url.startswith("/dados/") else None
                if old_filepath and os.path.isfile(old_filepath):
                    os.remove(old_filepath)

            ext = file.content_type.split("/")[-1].replace("jpeg", "jpg")
            filename = f"{uuid.uuid4().hex}.{ext}"
            user_dir = os.path.join(AVATAR_BASE_DIR, str(user_id))
            os.makedirs(user_dir, exist_ok=True)

            filepath = os.path.join(user_dir, filename)
            with open(filepath, "wb") as f:
                f.write(contents)

            relative_path = filepath.replace("/dados", "", 1)
            app_url = os.getenv("APP_URL", "http://localhost:8000")
            public_url = f"{app_url}/dados{relative_path}"

            user.avatar_url = public_url
            await db.commit()

            return success("Avatar atualizado com sucesso", {"avatar_url": public_url})

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao atualizar avatar: {str(e)}")
