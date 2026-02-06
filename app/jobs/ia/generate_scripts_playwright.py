import logging
import os

import app.core.database.models  
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService
from app.modules.ai.utils.ai_utils import AiUtils

from app.modules.ai.service.scripts_playwright_service import ScriptsPlaywrightAgent
from app.modules.playwright.model.playwright_script_model import PlaywrightScript
from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis  


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
        
        updated_status = (
            db.query(QaAnalysis)
            .filter(QaAnalysis.id == analysis_id, QaAnalysis.user_id == user_id)
            .update(
                {
                    "status": 'generating_scripts'
                },
                synchronize_session=False,
            )
        )
        
        db.commit()

        scripts_playwright_prompt = AiUtils.build_playwright_script_prompt(
            analysis=analysis_payload,
        )

        logger.info(
            "🧠 Prompt Playwright gerado",
            extra={"analysis_id": analysis_id, "user_id": user_id},
        )

        ai_model_used = os.getenv("OPENAI_MODEL_PLAYWRIGHT", "gpt-4.1-mini")
        agent = ScriptsPlaywrightAgent(model=ai_model_used)

        result = agent.generate(scripts_playwright_prompt)

        # 3) salvar no banco
        # versão: pega última versão do analysis e incrementa
        last_version = (
            db.query(PlaywrightScript.version)
            .filter(PlaywrightScript.analysis_id == analysis_id)
            .order_by(PlaywrightScript.version.desc())
            .limit(1)
            .scalar()
        )
        next_version = int(last_version or 0) + 1

        script_row = PlaywrightScript(
            analysis_id=analysis_id,
            title=result["title"],
            version=next_version,
            language=result["language"],
            status="generated",
            script=result["script"],
            generator_model=ai_model_used,
            meta={
                "source": "celery_job",
            },
        )

        db.add(script_row)

        analysis = db.query(QaAnalysis).filter(QaAnalysis.id == analysis_id).first()
        analysis.status = "scripts_generated"

        db.commit()

        logger.info(
            "✅ Script Playwright salvo com sucesso",
            extra={
                "analysis_id": analysis_id,
                "user_id": user_id,
                "script_id": script_row.id,
                "version": next_version,
            },
        )

        return {
            "analysis_id": analysis_id,
            "script_id": script_row.id,
            "version": next_version,
            "status": "completed",
        }

    except Exception:
        db.rollback()
        logger.exception("❌ Erro no job generate_scripts_playwright")
        raise

    finally:
        db.close()
