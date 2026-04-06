"""Controle de status dos jobs de IA por alvo (Target)."""
import logging
from datetime import datetime, timezone
from sqlalchemy import func

from app.modules.target.model.target_model import Target
from app.modules.target.model.target_job_model import TargetJob

logger = logging.getLogger(__name__)


def mark_job_running(db, target_id: int, job_type: str) -> None:
    db.query(TargetJob).filter(
        TargetJob.target_id == target_id,
        TargetJob.job_type == job_type,
    ).update(
        {"status": "running", "started_at": datetime.now(timezone.utc)},
        synchronize_session=False,
    )


def mark_job_completed(db, target_id: int, job_type: str) -> None:
    db.query(TargetJob).filter(
        TargetJob.target_id == target_id,
        TargetJob.job_type == job_type,
    ).update(
        {"status": "completed", "completed_at": datetime.now(timezone.utc)},
        synchronize_session=False,
    )

    target = (
        db.query(Target)
        .filter(Target.id == target_id)
        .with_for_update()
        .first()
    )
    if target is None:
        return

    pending_count = (
        db.query(func.count(TargetJob.id))
        .filter(
            TargetJob.target_id == target_id,
            TargetJob.status.in_(["pending", "running"]),
        )
        .scalar()
    )

    if pending_count == 0:
        target.status = "completed"
        logger.info(f"[Jobs] Todos os jobs concluídos | target_id={target_id}")


def mark_job_error(db, target_id: int, job_type: str, error: Exception) -> None:
    db.query(TargetJob).filter(
        TargetJob.target_id == target_id,
        TargetJob.job_type == job_type,
    ).update(
        {"status": "error", "error_message": str(error)[:2000]},
        synchronize_session=False,
    )

    db.query(Target).filter(Target.id == target_id).update(
        {"status": "error"},
        synchronize_session=False,
    )
