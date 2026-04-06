import logging

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.target.model.target_model import Target
from app.modules.target.model.target_job_model import TargetJob
from app.modules.screen.model.screen_model import Screen
from app.modules.target.service.target_service import TargetService
from app.modules.ai.service.screen_explorer_service import ScreenExplorerService

logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.generate_screen_description",
    autoretry_for=(ValueError, RuntimeError),
    retry_kwargs={"max_retries": 2, "countdown": 60},
)
def generate_screen_description(*, analysis_id: int, user_id: int, requirements: list = None):
    """
    Explora a(s) tela(s) do alvo via BrowserUse.

    - Descrições de execução (tests_description, playwright_description) → salvas no Target
    - Descrições de conhecimento (documentation_description, uiux_description) → salvas em cada Screen
    """
    logger.info(
        "🚀 Job GenerateScreenDescription iniciado",
        extra={"target_id": analysis_id, "user_id": user_id},
    )

    db = SessionLocal()

    try:
        target_service = TargetService()
        explorer_service = ScreenExplorerService()

        # Carrega o target com suas screens
        target_payload = target_service.get_or_fail_sync(
            db=db,
            target_id=analysis_id,
            user_id=user_id,
        )

        if not isinstance(target_payload, dict):
            target_payload = target_payload.to_dict()

        # Obtém a primeira tela (tela primária para exploração)
        screens = target_payload.get("screens", [])
        if not screens:
            raise ValueError(f"Target {analysis_id} não possui telas associadas")

        primary_screen = screens[0]

        # Monta payload de análise compatível com o ScreenExplorerService
        analysis_payload = {
            "id": analysis_id,
            "name": target_payload.get("name"),
            "target_url": primary_screen.get("url"),
            "description": target_payload.get("description"),
            "screen_context": primary_screen.get("screen_context"),
            "access_credentials": primary_screen.get("access_credentials", []),
        }

        db.query(Target).filter(
            Target.id == analysis_id
        ).update({"status": "generating"}, synchronize_session=False)
        db.commit()

        descriptions = explorer_service.generate_screen_descriptions(
            analysis=analysis_payload
        )

        # Salva descrições de execução no Target
        db.query(Target).filter(Target.id == analysis_id).update(
            {
                "tests_description": descriptions["tests_description"],
                "playwright_description": descriptions["playwright_description"],
            },
            synchronize_session=False,
        )

        # Salva descrições de conhecimento na Screen primária
        db.query(Screen).filter(Screen.id == primary_screen["id"]).update(
            {
                "documentation_description": descriptions["documentation_description"],
                "uiux_description": descriptions["uiux_description"],
            },
            synchronize_session=False,
        )

        db.commit()

        # -------------------------------------------------------
        # Monta os sub-jobs a disparar (documentação é por Screen, não por Target)
        # -------------------------------------------------------
        available_jobs = {
            "test_cases": "jobs.ia.generate_test_case",
            "scripts": "jobs.ia.generate_scripts_playwright",
        }

        targets_req = [r for r in (requirements or list(available_jobs.keys())) if r in available_jobs]
        valid_targets = targets_req

        db.query(TargetJob).filter(TargetJob.target_id == analysis_id).delete()
        for job_type in valid_targets:
            db.add(TargetJob(target_id=analysis_id, job_type=job_type, status="pending"))

        db.query(Target).filter(Target.id == analysis_id).update(
            {"status": "processing"}, synchronize_session=False
        )
        db.commit()

        for req in valid_targets:
            from app.core.celery_app import celery_app as app
            app.send_task(
                available_jobs[req],
                kwargs={"analysis_id": analysis_id, "user_id": user_id},
            )

        logger.info("✅ Job GenerateScreenDescription finalizado com sucesso")
        return {"target_id": analysis_id, "status": "processing", "jobs": valid_targets}

    except Exception:
        db.rollback()
        logger.exception("❌ Erro no job GenerateScreenDescription")

        retries_done = getattr(generate_screen_description.request, "retries", 0)
        max_retries = generate_screen_description.max_retries or 0
        if retries_done >= max_retries:
            try:
                db.query(Target).filter(Target.id == analysis_id).update(
                    {"status": "error"}, synchronize_session=False
                )
                db.commit()
            except Exception:
                db.rollback()

        raise

    finally:
        db.close()
