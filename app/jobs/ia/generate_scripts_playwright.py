import logging

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService
from app.modules.ai.utils.ai_utils import AiUtils

logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.generate_scripts_playwright",
    autoretry_for=(),
)
def generate_scripts_playwright(*, analysis_id: int, user_id: int):
    logger.info(
        "🚀 Job generate_scripts_playwright iniciado",
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


        # scripts_playwright_prompt = AiUtils.build_scripts_playwright_prompt(
        #     analysis=analysis_payload,
        # )

        logger.info("✅ Job generate_scripts_playwright finalizado com sucesso")

        return {"analysis_id": analysis_id, "status": "completed"}

    except Exception:
        db.rollback()
        logger.exception("❌ Erro no job generate_scripts_playwright")
        raise

    finally:
        db.close()
