import logging
from datetime import datetime

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.stress_test.model.stress_test_model import StressTest
from app.modules.stress_test.model.stress_test_finding_model import StressTestFinding

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@celery_app.task(name="jobs.ia.run_stress_test_aggregate")
def run_stress_test_aggregate(worker_results: list, stress_test_id: int):
    logger.info(f"[Agregador] Iniciando — stress_test_id={stress_test_id}, workers={len(worker_results)}")

    db = SessionLocal()
    try:
        findings = (
            db.query(StressTestFinding)
            .filter(StressTestFinding.stress_test_id == stress_test_id)
            .all()
        )
        total = len(findings)

        failed_workers = [r for r in (worker_results or []) if isinstance(r, dict) and r.get("status") == "error"]

        summary = _build_summary(findings, failed_workers, worker_results or [])

        db.query(StressTest).filter(StressTest.id == stress_test_id).update(
            {
                "status": "completed",
                "summary": summary,
                "total_findings": total,
                "completed_at": datetime.utcnow(),
            },
            synchronize_session=False,
        )
        db.commit()

        logger.info(f"[Agregador] Concluído: {total} findings — stress_test_id={stress_test_id}")
        return {"stress_test_id": stress_test_id, "total_findings": total}

    except Exception as exc:
        db.rollback()
        logger.exception(f"[Agregador] Erro — stress_test_id={stress_test_id}")
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


def _build_summary(findings: list, failed_workers: list, worker_results: list) -> str:
    total = len(findings)

    if total == 0 and not failed_workers:
        return (
            "Stress test concluído. Nenhum bug encontrado. "
            "A interface se comportou corretamente em todos os cenários executados."
        )

    severity_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = getattr(f, "severity", None) or "low"
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    parts = [f"Stress test concluído. {total} bug(s) encontrado(s)."]

    breakdown = ", ".join(
        f"{v} {k}"
        for k, v in severity_counts.items()
        if v > 0
    )
    if breakdown:
        parts.append(f"Severidades: {breakdown}.")

    workers_ok = [r for r in worker_results if isinstance(r, dict) and r.get("status") == "completed"]
    parts.append(f"{len(workers_ok)} worker(s) concluído(s) com sucesso.")

    if failed_workers:
        ids = [str(r.get("worker_id", "?")) for r in failed_workers]
        parts.append(f"ATENÇÃO: {len(failed_workers)} worker(s) falharam (IDs: {', '.join(ids)}) — cobertura parcial.")

    return " ".join(parts)
