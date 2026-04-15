import os
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.modules.screen.model.screen_model import Screen
from app.modules.screen.model.screen_document_model import ScreenDocument
from app.modules.screen.model.access_credential_model import AccessCredential
from app.modules.user.model.user_model import User

BASE_PATH = "storage/screens"

ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown"
}


class ScreenService:

    def _serialize(self, screen: Screen, include_docs: bool = False) -> dict:
        data = screen.to_dict()
        data["access_credentials"] = screen.access_credentials or []
        
        if include_docs:
            data["documents"] = [
                {"id": doc.id, "type": doc.type, "path": doc.path}
                for doc in (screen.documents or [])
            ]
        return data

    async def list_by_owner(self, db: AsyncSession, user_id: int, owner_type: str, owner_id: int):
        try:
            result = await db.execute(
                select(Screen)
                .options(
                    selectinload(Screen.documents),
                    selectinload(Screen.access_credentials),
                )
                .where(
                    Screen.owner_type == owner_type,
                    Screen.owner_id == owner_id,
                    Screen.deleted_at.is_(None),
                )
            )
            screens = result.scalars().unique().all()

            return [self._serialize(s, include_docs=True) for s in screens]

        except Exception as e:
            raise ValueError(f"Erro ao listar telas: {str(e)}")

    async def get_or_fail(self, db: AsyncSession, screen_id: int, user_id: int):
        try:
            result = await db.execute(
                select(Screen)
                .options(
                    selectinload(Screen.documents),
                    selectinload(Screen.access_credentials),
                )
                .where(
                    Screen.id == screen_id,
                    Screen.user_id == user_id,
                    Screen.deleted_at.is_(None),
                )
            )
            screen = result.scalar_one_or_none()

            if not screen:
                raise ValueError("Tela não encontrada")

            return self._serialize(screen, include_docs=True)

        except Exception as e:
            raise ValueError(str(e))

    def get_or_fail_sync(self, db, screen_id: int, user_id: int):
        from sqlalchemy.orm import selectinload as sync_selectinload

        screen = (
            db.query(Screen)
            .options(
                sync_selectinload(Screen.documents),
                sync_selectinload(Screen.access_credentials),
            )
            .filter(Screen.id == screen_id, Screen.user_id == user_id, Screen.deleted_at.is_(None))
            .first()
        )

        if not screen:
            raise ValueError("Tela não encontrada")

        return self._serialize(screen, include_docs=True)

    async def create_with_documents(
        self,
        db: AsyncSession,
        data: dict,
        documents: list,
        access_credentials: list | None = None,
    ):
        try:
            result_user = await db.execute(select(User).where(User.id == data["user_id"]))
            if not result_user.scalar_one_or_none():
                raise ValueError("Usuário não encontrado")

            screen = Screen(**data)
            db.add(screen)
            await db.flush()

            folder = os.path.join(BASE_PATH, str(screen.id))
            os.makedirs(folder, exist_ok=True)

            saved_docs = []
            for file in documents:
                if file.content_type not in ALLOWED_TYPES:
                    raise ValueError(f"Tipo não permitido: {file.content_type}")

                ext = os.path.splitext(file.filename)[1]
                filename = f"{uuid.uuid4()}{ext}"
                path = os.path.join(folder, filename)

                with open(path, "wb") as f:
                    f.write(await file.read())

                doc = ScreenDocument(screen_id=screen.id, type=file.content_type, path=path)
                db.add(doc)
                saved_docs.append(doc)

            saved_credentials = []
            if access_credentials:
                for cred in access_credentials:
                    if "field_name" not in cred or "value" not in cred:
                        raise ValueError("Credencial inválida")
                    credential = AccessCredential(
                        screen_id=screen.id,
                        field_name=cred["field_name"],
                        value=cred["value"],
                    )
                    db.add(credential)
                    saved_credentials.append(credential)

            await db.commit()
            await db.refresh(screen)

            return {
                **screen.to_dict(),
                "documents": [
                    {"id": doc.id, "type": doc.type, "path": doc.path}
                    for doc in saved_docs
                ],
                "access_credentials": [
                    {"id": c.id, "field_name": c.field_name}
                    for c in saved_credentials
                ],
            }

        except IntegrityError:
            await db.rollback()
            raise ValueError("Erro de integridade ao criar tela")

        except Exception as e:
            await db.rollback()
            raise ValueError(str(e))

    async def update(self, db: AsyncSession, screen_id: int, data: dict, user_id: int):
        try:
            result = await db.execute(
                select(Screen)
                .options(selectinload(Screen.access_credentials))
                .where(Screen.id == screen_id, Screen.user_id == user_id)
            )
            screen = result.scalar_one_or_none()

            if not screen:
                raise ValueError("Tela não encontrada")

            access_credentials = data.pop("access_credentials", None)

            for field, value in data.items():
                if value is not None and hasattr(screen, field):
                    setattr(screen, field, value)

            if access_credentials is not None:
                for cred in screen.access_credentials:
                    await db.delete(cred)

                for cred in access_credentials:
                    db.add(AccessCredential(
                        screen_id=screen.id,
                        field_name=cred["field_name"],
                        value=cred["value"],
                    ))

            await db.commit()

            result = await db.execute(
                select(Screen)
                .options(selectinload(Screen.access_credentials))
                .where(Screen.id == screen_id)
            )
            screen = result.scalar_one()

            return self._serialize(screen)

        except Exception as e:
            await db.rollback()
            raise ValueError(str(e))

    async def delete(self, db: AsyncSession, screen_id: int, user_id: int):
        try:
            result = await db.execute(
                select(Screen).where(
                    Screen.id == screen_id,
                    Screen.user_id == user_id,
                    Screen.deleted_at.is_(None),
                )
            )
            screen = result.scalar_one_or_none()

            if not screen:
                raise ValueError("Tela não encontrada")

            screen.deleted_at = datetime.utcnow()
            await db.commit()

        except Exception as e:
            await db.rollback()
            raise ValueError(str(e))

    async def restore(self, db: AsyncSession, screen_id: int, user_id: int):
        try:
            result = await db.execute(
                select(Screen).where(Screen.id == screen_id, Screen.user_id == user_id)
            )
            screen = result.scalar_one_or_none()

            if not screen:
                raise ValueError("Tela não encontrada")

            if screen.deleted_at is None:
                raise ValueError("Tela não está deletada")

            screen.deleted_at = None
            await db.commit()
            await db.refresh(screen)
            return screen.to_dict()

        except Exception as e:
            await db.rollback()
            raise ValueError(str(e))
