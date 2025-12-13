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

    async def create_with_documents(
        self,
        db: AsyncSession,
        data: dict,
        documents: list
    ):
        # 🔹 valida user_id antes de tudo
        user = await db.execute(
            select(User).where(User.id == data["user_id"])
        )
        if not user.scalar_one_or_none():
            raise ValueError("Usuário não encontrado")

        analysis = QaAnalysis(**data)
        db.add(analysis)

        try:
            await db.flush()  # pode quebrar FK, unique, etc
        except IntegrityError as e:
            await db.rollback()
            raise ValueError("Erro de integridade ao criar análise") from e

        # 📁 cria pasta
        folder = os.path.join(BASE_PATH, str(analysis.id))
        os.makedirs(folder, exist_ok=True)

        try:
            for file in documents:
                if file.content_type not in ALLOWED_TYPES:
                    raise ValueError(f"Tipo de arquivo não permitido: {file.content_type}")

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
