import json
import logging
from datetime import datetime

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.stress_test.model.stress_test_model import StressTest
from app.modules.target.service.target_service import TargetService
from app.modules.ai.service.stress_test_recon_service import (
    StressTestReconService,
    PageNotLoadedError,
    NoElementsFoundError,
)
from app.modules.ai.utils.ai_utils import AiUtils

logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.run_stress_test",
    autoretry_for=(RuntimeError,),
    retry_kwargs={"max_retries": 0},
)
def run_stress_test(*, stress_test_id: int, target_id: int, user_id: int):
    from celery import chord, group
    from app.jobs.ia.run_stress_test_worker import run_stress_test_worker
    from app.jobs.ia.run_stress_test_aggregate import run_stress_test_aggregate

    logger.info(f"[Orquestrador] Iniciando stress_test_id={stress_test_id}")

    db = SessionLocal()
    try:
        target_service = TargetService()
        target_payload = target_service.get_or_fail_sync(db=db, target_id=target_id, user_id=user_id)

        screens = target_payload.get("screens", [])
        if not screens:
            raise ValueError(f"Target {target_id} não possui telas associadas")

        primary_screen = screens[0]
        analysis = {
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

        # --- Fase 1: Reconhecimento (síncrono dentro desta task) ---
        logger.info(f"[Orquestrador] Iniciando reconhecimento — stress_test_id={stress_test_id}")
        recon_service = StressTestReconService()
        element_map = recon_service.run_recon(analysis=analysis)

        db.query(StressTest).filter(StressTest.id == stress_test_id).update(
            {"element_map": json.dumps(element_map, ensure_ascii=False)},
            synchronize_session=False,
        )
        db.commit()

        fields  = element_map.get("fields")  or []
        buttons = element_map.get("buttons") or []
        logger.info(
            f"[Orquestrador] Reconhecimento concluído: "
            f"{len(fields)} campos, {len(buttons)} botões — stress_test_id={stress_test_id}"
        )

        # --- Fase 2: Classificação e divisão em batches (Python puro) ---
        batches = AiUtils.create_worker_batches(element_map)

        if not batches:
            raise ValueError("Nenhum elemento encontrado para atacar após o reconhecimento")

        db.query(StressTest).filter(StressTest.id == stress_test_id).update(
            {"worker_batches": json.dumps(
                [[{k: v for k, v in e.items()} for e in b] for b in batches],
                ensure_ascii=False,
            )},
            synchronize_session=False,
        )
        db.commit()

        logger.info(
            f"[Orquestrador] {len(batches)} batch(es) criado(s) — "
            f"disparando workers em paralelo — stress_test_id={stress_test_id}"
        )

        # --- Fase 3: Chord de workers → agregador ---
        worker_tasks = group(
            run_stress_test_worker.s(
                stress_test_id=stress_test_id,
                target_id=target_id,
                user_id=user_id,
                worker_id=i,
                batch=batches[i],
            )
            for i in range(len(batches))
        )
        chord(worker_tasks)(
            run_stress_test_aggregate.s(stress_test_id=stress_test_id)
        )

        logger.info(f"[Orquestrador] Chord disparado — stress_test_id={stress_test_id}")

    except Exception as exc:
        db.rollback()
        logger.exception(f"[Orquestrador] Erro — stress_test_id={stress_test_id}")
        try:
            db.query(StressTest).filter(StressTest.id == stress_test_id).update(
                {"status": "error", "error_message": _friendly_error(exc)},
                synchronize_session=False,
            )
            db.commit()
        except Exception:
            db.rollback()
        raise

    finally:
        db.close()


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, PageNotLoadedError):
        return "Não foi possível carregar a página. Verifique se a URL está acessível e tente novamente."
    if isinstance(exc, NoElementsFoundError):
        return "Nenhum campo ou botão interativo foi encontrado na página. Verifique se a URL está correta."
    msg = str(exc).lower()
    if "não possui telas" in msg:
        return "Este alvo não possui nenhuma tela configurada."
    return "Ocorreu um erro durante a análise. Tente novamente em alguns instantes."
