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

        documents_block = None
        documents_text = None

        # suporta analysis como objeto OU dict
        documents = (
            analysis.get("documents")
            if isinstance(analysis, dict)
            else getattr(analysis, "documents", None)
        )

        if documents:
            documents_text = AiUtils.read_documents_with_docling(
                documents=documents
            )

            if documents_text and documents_text.strip():
                documents_block = AiUtils.build_documents_block(
                    documents_text
                )


        analysis_payload = (
            analysis if isinstance(analysis, dict) else analysis.to_dict()
        )


        test_case_prompt = AiUtils.build_test_case_prompt(
            ui_description=ui_description,
            analysis=analysis_payload,
            documents_block=documents_block,
        )


        celery_app.send_task(
            "jobs.ia.generate_test_case",
            kwargs={
                "analysis_id": analysis_id,
                "user_id": user_id,
                "test_case_prompt": test_case_prompt,
            },
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
