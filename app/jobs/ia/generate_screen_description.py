import logging

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from app.modules.qa_analysis.model.analysis_job_model import AnalysisJob
from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService
from app.modules.ai.service.screen_explorer_service import ScreenExplorerService

logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.generate_screen_description",
    autoretry_for=(ValueError, RuntimeError),
    retry_kwargs={"max_retries": 2, "countdown": 60},
)
def generate_screen_description(*, analysis_id: int, user_id: int, requirements: list = None):
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

        db.query(QaAnalysis).filter(
            QaAnalysis.id == analysis_id, QaAnalysis.user_id == user_id
        ).update({"status": "generating"}, synchronize_session=False)
        db.commit()

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
                f"Falha ao persistir descrições: updated_rows={updated_rows} analysis_id={analysis_id}"
            )

        db.commit()

        # -------------------------------------------------------
        # Monta os sub-jobs a disparar
        # -------------------------------------------------------
        available_jobs = {
            "test_cases": "jobs.ia.generate_test_case",
            "scripts": "jobs.ia.generate_scripts_playwright",
            "documentation": "jobs.ia.generate_documentation",
        }

        targets = requirements if requirements else list(available_jobs.keys())
        valid_targets = [req for req in targets if req in available_jobs]

        # Limpa jobs anteriores (idempotência em caso de retry) e cria novos como pending
        db.query(AnalysisJob).filter(AnalysisJob.qa_analysis_id == analysis_id).delete()
        for job_type in valid_targets:
            db.add(AnalysisJob(qa_analysis_id=analysis_id, job_type=job_type, status="pending"))

        db.query(QaAnalysis).filter(QaAnalysis.id == analysis_id).update(
            {"status": "processing"}, synchronize_session=False
        )
        db.commit()

        for req in valid_targets:
            celery_app.send_task(
                available_jobs[req],
                kwargs={"analysis_id": analysis_id, "user_id": user_id},
            )

        logger.info("✅ Job GenerateScreenDescription finalizado com sucesso")
        return {"analysis_id": analysis_id, "status": "processing", "jobs": valid_targets}

    except Exception:
        db.rollback()
        logger.exception("❌ Erro no job GenerateScreenDescription")

        # Só marca status=error se esgotou todos os retries
        retries_done = getattr(generate_screen_description.request, "retries", 0)
        max_retries = generate_screen_description.max_retries or 0
        if retries_done >= max_retries:
            try:
                db.query(QaAnalysis).filter(QaAnalysis.id == analysis_id).update(
                    {"status": "error"}, synchronize_session=False
                )
                db.commit()
            except Exception:
                db.rollback()

        raise

    finally:
        db.close()
