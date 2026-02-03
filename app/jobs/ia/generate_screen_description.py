import logging

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
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

        analysis_payload = qa_service.get_or_fail_sync(
            db=db,
            entity_id=analysis_id,
            user_id=user_id,
        )

        if not isinstance(analysis_payload, dict):
            analysis_payload = analysis_payload.to_dict()

        descriptions = explorer_service.generate_screen_descriptions(
            analysis=analysis_payload
        )

        updated_rows = (
            db.query(QaAnalysis)
            .filter(QaAnalysis.id == analysis_id, QaAnalysis.user_id == user_id)
            .update(
                {
                    "tests_description": descriptions["tests_description"],
                    "playwright_description": descriptions["playwright_description"],
                    "documentation_description": descriptions["documentation_description"],
                    "uiux_description": descriptions["uiux_description"],
                },
                synchronize_session=False,
            )
        )

        if updated_rows != 1:
            raise RuntimeError(
                f"Falha ao persistir descrições: updated_rows={updated_rows} analysis_id={analysis_id} user_id={user_id}"
            )

        db.commit()

        documents_block = None
        documents_text = None

        documents = analysis_payload.get("documents")

        if documents:
            documents_text = AiUtils.read_documents_with_docling(documents=documents)
            if documents_text and documents_text.strip():
                documents_block = AiUtils.build_documents_block(documents_text)

        test_case_prompt = AiUtils.build_test_case_prompt(
            ui_description=descriptions["tests_description"],
            analysis=analysis_payload,
            documents_block=documents_block,
        )

        celery_app.send_task(
            "jobs.ia.generate_test_case",
            kwargs={
                "qa_analysis_id": analysis_id,
                "user_id": user_id,
                "test_case_prompt": test_case_prompt,
            },
        )

        logger.info("✅ Job GenerateScreenDescription finalizado com sucesso")

        return {"analysis_id": analysis_id, "status": "completed"}

    except Exception:
        db.rollback()
        logger.exception("❌ Erro no job GenerateScreenDescription")
        raise

    finally:
        db.close()
