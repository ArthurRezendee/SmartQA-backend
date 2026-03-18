import logging
import os
import hashlib

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService
from app.modules.ai.utils.ai_utils import AiUtils
from app.modules.ai.service.docs_generator_service import DocumentationAgent
from app.modules.documentation.model.documentation_model import Documentation
from app.jobs.ia._jobs import mark_job_running, mark_job_completed, mark_job_error
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
        mark_job_running(db, analysis_id, "documentation")
        db.commit()

        qa_service = QaAnalysisService()

        analysis_payload = qa_service.get_or_fail_sync(
            db=db,
            entity_id=analysis_id,
            user_id=user_id,
        )

        if not isinstance(analysis_payload, dict):
            analysis_payload = analysis_payload.to_dict()

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

        mark_job_completed(db, analysis_id, "documentation")
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

    except Exception as e:
        db.rollback()
        logger.exception("❌ Erro no job generate_documentation")

        retries_done = getattr(generate_documentation.request, "retries", 0)
        max_retries = generate_documentation.max_retries or 0
        if retries_done >= max_retries:
            try:
                mark_job_error(db, analysis_id, "documentation", e)
                db.commit()
            except Exception:
                db.rollback()

        raise

    finally:
        db.close()
