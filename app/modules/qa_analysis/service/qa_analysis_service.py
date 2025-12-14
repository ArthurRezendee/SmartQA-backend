import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from app.modules.qa_analysis.model.qa_document_model import QaDocument
from app.modules.user.model.user_model import User


BASE_PATH = "storage/qa_analyses"
ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown"
}


class QaAnalysisService:

    async def list_by_user(self, db: AsyncSession, user_id: int):
        result = await db.execute(
            select(QaAnalysis).where(QaAnalysis.user_id == user_id)
        )
        return result.scalars().all()

    async def get_or_fail(self, db: AsyncSession, entity_id: int, user_id: int):
        result = await db.execute(
            select(QaAnalysis).where(
                QaAnalysis.id == entity_id,
                QaAnalysis.user_id == user_id
            )
        )
        record = result.scalar_one_or_none()

        if not record:
            raise ValueError("Análise não encontrada")

        return record

    async def create_with_documents(
        self,
        db: AsyncSession,
        data: dict,
        documents: list
    ):
        # 🔒 valida usuário
        user = await db.execute(
            select(User).where(User.id == data["user_id"])
        )
        if not user.scalar_one_or_none():
            raise ValueError("Usuário não encontrado")

        analysis = QaAnalysis(**data)
        db.add(analysis)

        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise ValueError("Erro ao criar análise")

        folder = os.path.join(BASE_PATH, str(analysis.id))
        os.makedirs(folder, exist_ok=True)

        try:
            for file in documents:
                if file.content_type not in ALLOWED_TYPES:
                    raise ValueError(f"Tipo não permitido: {file.content_type}")

                ext = os.path.splitext(file.filename)[1]
                filename = f"{uuid.uuid4()}{ext}"
                path = os.path.join(folder, filename)

                with open(path, "wb") as f:
                    f.write(await file.read())

                db.add(QaDocument(
                    qa_analysis_id=analysis.id,
                    type=file.content_type,
                    path=path
                ))

            await db.commit()

        except Exception as e:
            await db.rollback()
            raise ValueError(str(e))

        await db.refresh(analysis)
        return analysis

    async def update(self, db, entity_id: int, data: dict, user_id: int):
        record = await self.get_or_fail(db, entity_id, user_id)

        for key, value in data.items():
            setattr(record, key, value)

        await db.commit()
        await db.refresh(record)
        return record

    async def delete(self, db, entity_id: int, user_id: int):
        record = await self.get_or_fail(db, entity_id, user_id)
        await db.delete(record)
        await db.commit()
