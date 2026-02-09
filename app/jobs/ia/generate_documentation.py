import logging
import os
import hashlib

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService
from app.modules.ai.utils.ai_utils import AiUtils
from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from app.modules.ai.service.docs_generator_service import DocumentationAgent
from app.modules.documentation.model.documentation_model import Documentation
from sqlalchemy import func


logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.generate_documentation",
    autoretry_for=(),
)
def generate_documentation(*, analysis_id: int, user_id: int):
    logger.info(
        "🚀 Job generate_documentation iniciado",
        extra={"analysis_id": analysis_id, "user_id": user_id},
    )

    db = SessionLocal()

    try:
        qa_service = QaAnalysisService()

        analysis_payload = qa_service.get_or_fail_sync(
            db=db,
            entity_id=analysis_id,
            user_id=user_id,
        )

        if not isinstance(analysis_payload, dict):
            analysis_payload = analysis_payload.to_dict()

        # Atualiza status → generating_docs
        db.query(QaAnalysis).filter(
            QaAnalysis.id == analysis_id,
            QaAnalysis.user_id == user_id,
        ).update(
            {"status": "generating_docs"},
            synchronize_session=False,
        )
        db.commit()

        # Gera prompt
        docs_prompt = AiUtils.build_docs_prompt(
            analysis=analysis_payload,
        )

        logger.info(
            "🧠 Prompt Docs gerado",
            extra={"analysis_id": analysis_id, "user_id": user_id},
        )

        ai_model_used = os.getenv("OPENAI_MODEL_DOCS", "gpt-4.1-mini")

        # Gera documentação
        agent = DocumentationAgent(model=ai_model_used)
        documentation_text = agent.generate(docs_prompt)

        # Próxima versão
        last_version = (
            db.query(func.max(Documentation.version))
            .filter(Documentation.qa_analysis_id == analysis_id)
            .scalar()
        ) or 0

        next_version = last_version + 1

        # Title NUNCA pode ser null
        title = (
            analysis_payload.get("name")
            or f"Documentação funcional - Analysis {analysis_id}"
        )

        prompt_hash = hashlib.sha256(docs_prompt.encode()).hexdigest()

        documentation = Documentation(
            qa_analysis_id=analysis_id,
            title=title,
            version=next_version,
            status="generated",
            content=documentation_text,
            content_format="text",
            generated_by="ai",
            generator_model=ai_model_used,
            prompt_hash=prompt_hash,
        )

        db.add(documentation)

        # Atualiza status final do analysis
        analysis = db.query(QaAnalysis).filter(QaAnalysis.id == analysis_id).first()
        analysis.status = "docs_generated"

        db.commit()

        logger.info(
            "✅ Documentação gerada e salva com sucesso",
            extra={"analysis_id": analysis_id, "version": next_version},
        )

        return {
            "analysis_id": analysis_id,
            "documentation_version": next_version,
            "status": "completed",
        }

    except Exception:
        db.rollback()
        logger.exception("❌ Erro no job generate_documentation")
        raise

    finally:
        db.close()
