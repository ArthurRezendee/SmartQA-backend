import logging

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService
from app.modules.ai.service.screen_explorer_service import ScreenExplorerService
from app.modules.ai.utils.ai_utils import AiUtils


logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.generate_screen_description",
    autoretry_for=(),
)
def generate_screen_description(*, analysis_id: int, user_id: int):
    logger.info(
        "🚀 Job GenerateScreenDescription iniciado",
        extra={"analysis_id": analysis_id, "user_id": user_id},
    )

    db = SessionLocal()

    try:
        qa_service = QaAnalysisService()
        explorer_service = ScreenExplorerService()

        analysis = qa_service.get_or_fail_sync(
            db=db,
            entity_id=analysis_id,
            user_id=user_id,
        )

        ui_description = explorer_service.generate_ui_description(
            analysis=analysis
        )

        test_case_prompt = AiUtils.build_test_case_prompt(
            ui_description=ui_description,
            analysis=analysis,
        )

        logger.info(f"🖥️ UI DESCRIPTION:\n{ui_description}")
        logger.info(f"🧪 TEST CASE PROMPT:\n{test_case_prompt}")

        logger.info("✅ Job GenerateScreenDescription finalizado com sucesso")

        return {
            "analysis_id": analysis_id,
            "status": "completed",
        }

    except Exception:
        logger.exception("❌ Erro no job GenerateScreenDescription")
        raise

    finally:
        db.close()
