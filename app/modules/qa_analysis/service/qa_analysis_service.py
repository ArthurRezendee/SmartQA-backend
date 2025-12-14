import os
import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from app.modules.qa_analysis.model.qa_document_model import QaDocument
from app.modules.qa_analysis.model.access_credential_model import AccessCredential
from app.modules.user.model.user_model import User


BASE_PATH = "storage/qa_analyses"
ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown"
}


class QaAnalysisService:

    async def list_by_user(self, db: AsyncSession, user_id: int):
        try:
            result = await db.execute(
                select(QaAnalysis)
                .options(
                    selectinload(QaAnalysis.documents),
                    selectinload(QaAnalysis.access_credentials)
                )
                .where(QaAnalysis.user_id == user_id)
            )

            analyses = result.scalars().unique().all()

            return [
                {
                    **analysis.to_dict(),
                    "documents": [
                        {
                            "id": doc.id,
                            "type": doc.type,
                            "path": doc.path
                        } for doc in analysis.documents
                    ],
                    "access_credentials": [
                        {
                            "id": cred.id,
                            "field_name": cred.field_name
                        } for cred in analysis.access_credentials
                    ]
                }
                for analysis in analyses
            ]

        except Exception as e:
            raise ValueError(f"Erro ao listar análises: {str(e)}")

    async def get_or_fail(self, db: AsyncSession, entity_id: int, user_id: int):
        try:
            result = await db.execute(
                select(QaAnalysis)
                .options(
                    selectinload(QaAnalysis.documents),
                    selectinload(QaAnalysis.access_credentials)
                )
                .where(
                    QaAnalysis.id == entity_id,
                    QaAnalysis.user_id == user_id
                )
            )

            analysis = result.scalar_one_or_none()

            if not analysis:
                raise ValueError("Análise não encontrada")

            return {
                **analysis.to_dict(),
                "documents": [
                    {
                        "id": doc.id,
                        "type": doc.type,
                        "path": doc.path
                    } for doc in analysis.documents
                ],
                "access_credentials": [
                    {
                        "id": cred.id,
                        "field_name": cred.field_name,
                        "value": cred.value
                    } for cred in analysis.access_credentials
                ]
            }

        except Exception as e:
            raise ValueError(str(e))

    async def create_with_documents(
        self,
        db: AsyncSession,
        data: dict,
        documents: list,
        access_credentials: list | None = None
    ):
        try:
            user = await db.execute(
                select(User).where(User.id == data["user_id"])
            )

            if not user.scalar_one_or_none():
                raise ValueError("Usuário não encontrado")

            analysis = QaAnalysis(**data)
            db.add(analysis)
            await db.flush()

            # 📄 DOCUMENTOS
            folder = os.path.join(BASE_PATH, str(analysis.id))
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

                doc = QaDocument(
                    qa_analysis_id=analysis.id,
                    type=file.content_type,
                    path=path
                )

                db.add(doc)
                saved_docs.append(doc)

            # 🔐 CREDENCIAIS (OPCIONAL)
            saved_credentials = []

            if access_credentials:
                for cred in access_credentials:
                    if "field_name" not in cred or "value" not in cred:
                        raise ValueError("Credencial inválida")

                    credential = AccessCredential(
                        qa_analysis_id=analysis.id,
                        field_name=cred["field_name"],
                        value=cred["value"]
                    )

                    db.add(credential)
                    saved_credentials.append(credential)

            await db.commit()
            await db.refresh(analysis)

            return {
                **analysis.to_dict(),
                "documents": [
                    {
                        "id": doc.id,
                        "type": doc.type,
                        "path": doc.path
                    } for doc in saved_docs
                ],
                "access_credentials": [
                    {
                        "id": cred.id,
                        "field_name": cred.field_name
                    } for cred in saved_credentials
                ]
            }

        except IntegrityError:
            await db.rollback()
            raise ValueError("Erro de integridade ao criar análise")

        except Exception as e:
            await db.rollback()
            raise ValueError(str(e))
