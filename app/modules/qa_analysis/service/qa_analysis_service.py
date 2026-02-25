import os
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from app.modules.qa_analysis.model.qa_document_model import QaDocument
from app.modules.qa_analysis.model.access_credential_model import AccessCredential
from app.modules.user.model.user_model import User
from app.modules.billing.model.billing_account_model import BillingAccount
from app.modules.plans.model.plan_model import Plan

BASE_PATH = "storage/qa_analyses"

ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown"
}


class QaAnalysisService:

    async def _validate_and_consume_analysis_quota(
        self,
        db: AsyncSession,
        user_id: int
    ):
        """
        Valida se o usuário pode criar nova análise
        e consome 1 unidade do ciclo atual.
        """

        result = await db.execute(
            select(BillingAccount)
            .options(selectinload(BillingAccount.plan))
            .where(
                BillingAccount.owner_user_id == user_id,
                BillingAccount.is_active == True
            )
        )

        billing = result.scalar_one_or_none()

        if not billing:
            raise ValueError("Usuário sem billing account ativa")

        if billing.subscription_status != "active":
            raise ValueError("Assinatura inativa")

        # 🔁 Reset automático se ciclo expirou
        now = datetime.utcnow()
        if billing.current_period_end and now > billing.current_period_end:
            billing.analyses_used_current_cycle = 0
            billing.current_period_start = now
            billing.current_period_end = now.replace(
                day=now.day
            )  # mantém padrão simples mensal

        plan = billing.plan

        allowed = (
            plan.analyses_per_month
            + billing.extra_credits
            - billing.analyses_used_current_cycle
        )

        if allowed <= 0:
            raise ValueError("Limite mensal de análises atingido")

        # 🔥 Consome 1 análise
        billing.analyses_used_current_cycle += 1

        await db.flush()

        return True


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
        
        
    def get_or_fail_sync(self, db, entity_id: int, user_id: int):
        try:
            analysis = (
                db.query(QaAnalysis)
                .options(
                    selectinload(QaAnalysis.documents),
                    selectinload(QaAnalysis.access_credentials)
                )
                .filter(
                    QaAnalysis.id == entity_id,
                    QaAnalysis.user_id == user_id
                )
                .first()
            )

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
            result_user = await db.execute(
                select(User).where(User.id == data["user_id"])
            )

            if not result_user.scalar_one_or_none():
                raise ValueError("Usuário não encontrado")

            await self._validate_and_consume_analysis_quota(
                db,
                data["user_id"]
            )

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

            # 🔐 CREDENCIAIS
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