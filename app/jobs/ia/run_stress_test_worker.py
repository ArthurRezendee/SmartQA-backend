import json
import logging

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.stress_test.model.stress_test_finding_model import StressTestFinding
from app.modules.stress_test.model.stress_test_step_model import StressTestStep
from app.modules.target.service.target_service import TargetService
from app.modules.ai.service.stress_test_worker_service import StressTestWorkerService

logger = logging.getLogger(__name__)

_VALID_SEVERITIES = {"critical", "high", "medium", "low"}
_VALID_CATEGORIES = {"crash", "validation", "ui_error", "http_error", "security", "functional", "ux"}
_VALID_RESULTS    = {"ok", "bug", "skipped"}


@celery_app.task(
    name="jobs.ia.run_stress_test_worker",
    autoretry_for=(),
    retry_kwargs={"max_retries": 0},
)
def run_stress_test_worker(
    *,
    stress_test_id: int,
    target_id: int,
    user_id: int,
    worker_id: int,
    batch: list,
):
    logger.info(f"[Worker {worker_id}] Iniciando — stress_test_id={stress_test_id}, batch_size={len(batch)}")

    db = SessionLocal()
    try:
        target_service = TargetService()
        target_payload = target_service.get_or_fail_sync(db=db, target_id=target_id, user_id=user_id)

        screens = target_payload.get("screens", [])
        primary_screen = screens[0] if screens else {}

        analysis = {
            "target_url": primary_screen.get("url"),
            "access_credentials": primary_screen.get("access_credentials", []),
        }

        worker_service = StressTestWorkerService()
        result = worker_service.run_worker(
            analysis=analysis,
            worker_id=worker_id,
            batch=batch,
            stress_test_id=stress_test_id,
        )

        findings_data = result.get("findings") or []
        attacks_log   = result.get("attacks_log") or []
        http_errors   = result.get("http_errors") or []

        # Enrich findings that have no error_details with captured HTTP errors
        if http_errors and findings_data:
            http_summary = "; ".join(
                f"{e.get('method','HTTP')} {e.get('url','')} → {e.get('status','?')}"
                for e in http_errors[:5]
            )
            for f in findings_data:
                if not f.get("error_details") or f.get("error_details") == "Nenhuma mensagem de erro foi exibida":
                    f["error_details"] = f"Erros HTTP capturados: {http_summary}"

        # --- 1. Salva findings e captura o mapa order → db_id ---
        order_to_finding_id: dict[int, int] = {}

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
            db.flush()  # gera o id antes de salvar os steps
            order_to_finding_id[int(f.get("order") or 0)] = finding.id

        # --- 2. Salva steps do attacks_log linkados aos findings ---
        # Monta lookup de field_type por label a partir do batch
        label_to_field_info = {
            e.get("label", ""): {
                "element_kind": e.get("element_kind"),
                "field_type":   e.get("field_type"),
            }
            for e in batch
        }

        for step_data in attacks_log:
            element_label = (step_data.get("element") or "")[:255]
            result_val    = _safe_enum(step_data.get("result"), _VALID_RESULTS, "ok")
            finding_order = step_data.get("finding_order")

            finding_id = None
            if result_val == "bug" and isinstance(finding_order, int):
                finding_id = order_to_finding_id.get(finding_order)

            field_info = label_to_field_info.get(element_label, {})
            attack_key = (step_data.get("attack_key") or "")[:50]

            step = StressTestStep(
                stress_test_id=stress_test_id,
                worker_id=worker_id,
                element_label=element_label,
                element_kind=field_info.get("element_kind") or step_data.get("element_kind"),
                field_type=field_info.get("field_type"),
                attack_key=attack_key,
                attack_description=_get_attack_description(attack_key),
                result=result_val,
                finding_id=finding_id,
            )
            db.add(step)

        db.commit()

        count = len(findings_data)
        steps_count = len(attacks_log)
        logger.info(
            f"[Worker {worker_id}] Concluído: {count} findings, "
            f"{steps_count} steps — stress_test_id={stress_test_id}"
        )
        return {"worker_id": worker_id, "findings_count": count, "steps_count": steps_count, "status": "completed"}

    except Exception as exc:
        db.rollback()
        logger.exception(f"[Worker {worker_id}] Erro — stress_test_id={stress_test_id}")
        return {"worker_id": worker_id, "findings_count": 0, "steps_count": 0, "status": "error", "error": str(exc)[:500]}

    finally:
        db.close()


def _safe_enum(val, valid_set: set, fallback: str) -> str:
    return val if val in valid_set else fallback


def _get_attack_description(attack_key: str) -> str | None:
    from app.modules.ai.utils.ai_utils import ATTACK_DESCRIPTIONS
    return ATTACK_DESCRIPTIONS.get(attack_key)
