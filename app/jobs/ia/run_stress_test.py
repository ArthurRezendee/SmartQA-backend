import json
import logging
from datetime import datetime

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.stress_test.model.stress_test_model import StressTest
from app.modules.stress_test.model.stress_test_finding_model import StressTestFinding
from app.modules.target.service.target_service import TargetService
from app.modules.ai.service.stress_test_agent_service import StressTestAgentService

logger = logging.getLogger(__name__)

_VALID_SEVERITIES = {"critical", "high", "medium", "low"}
_VALID_CATEGORIES = {"crash", "validation", "ui_error", "http_error", "security", "functional", "ux"}


@celery_app.task(
    name="jobs.ia.run_stress_test",
    autoretry_for=(RuntimeError,),
    retry_kwargs={"max_retries": 0},
)
def run_stress_test(*, stress_test_id: int, target_id: int, user_id: int):
    logger.info(f"🔥 Stress test iniciado: stress_test_id={stress_test_id}, target_id={target_id}")

    db = SessionLocal()

    try:
        target_service = TargetService()
        agent_service = StressTestAgentService()

        target_payload = target_service.get_or_fail_sync(db=db, target_id=target_id, user_id=user_id)

        screens = target_payload.get("screens", [])
        if not screens:
            raise ValueError(f"Target {target_id} não possui telas associadas")

        primary_screen = screens[0]

        analysis_payload = {
            "id": target_id,
            "name": target_payload.get("name"),
            "target_url": primary_screen.get("url"),
            "description": target_payload.get("description"),
            "screen_context": primary_screen.get("screen_context"),
            "access_credentials": primary_screen.get("access_credentials", []),
            "tests_description": target_payload.get("tests_description") or "",
        }

        db.query(StressTest).filter(StressTest.id == stress_test_id).update(
            {"status": "running", "started_at": datetime.utcnow()},
            synchronize_session=False,
        )
        db.commit()

        result = agent_service.run_stress_test(
            analysis=analysis_payload,
            stress_test_id=stress_test_id,
        )

        findings_data = result.get("findings") or []

        for f in findings_data:
            steps = f.get("steps_to_reproduce") or []
            finding = StressTestFinding(
                stress_test_id=stress_test_id,
                order_index=int(f.get("order") or 0),
                title=(f.get("title") or "Bug sem título")[:255],
                description=f.get("description"),
                severity=_safe_enum(f.get("severity"), _VALID_SEVERITIES, "medium"),
                category=_safe_enum(f.get("category"), _VALID_CATEGORIES, "functional"),
                element=f.get("element"),
                input_used=f.get("input_used"),
                steps_to_reproduce=json.dumps(steps, ensure_ascii=False) if steps else None,
                error_details=f.get("error_details"),
                screenshot_path=f.get("screenshot_path"),
            )
            db.add(finding)

        total = len(findings_data)

        db.query(StressTest).filter(StressTest.id == stress_test_id).update(
            {
                "status": "completed",
                "summary": result.get("summary"),
                "total_findings": total,
                "completed_at": datetime.utcnow(),
            },
            synchronize_session=False,
        )
        db.commit()

        logger.info(f"✅ Stress test concluído: {total} findings — stress_test_id={stress_test_id}")
        return {"stress_test_id": stress_test_id, "total_findings": total}

    except Exception as exc:
        db.rollback()
        logger.exception(f"❌ Erro no stress test stress_test_id={stress_test_id}")
        try:
            db.query(StressTest).filter(StressTest.id == stress_test_id).update(
                {"status": "error", "error_message": str(exc)[:2000]},
                synchronize_session=False,
            )
            db.commit()
        except Exception:
            db.rollback()
        raise

    finally:
        db.close()


def _safe_enum(val, valid_set: set, fallback: str) -> str:
    return val if val in valid_set else fallback
