"""Controle de status dos jobs de IA por análise."""
import logging
from datetime import datetime, timezone
from sqlalchemy import func

from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from app.modules.qa_analysis.model.analysis_job_model import AnalysisJob

logger = logging.getLogger(__name__)


def mark_job_running(db, analysis_id: int, job_type: str) -> None:
    db.query(AnalysisJob).filter(
        AnalysisJob.qa_analysis_id == analysis_id,
        AnalysisJob.job_type == job_type,
    ).update(
        {"status": "running", "started_at": datetime.now(timezone.utc)},
        synchronize_session=False,
    )


def mark_job_completed(db, analysis_id: int, job_type: str) -> None:
    db.query(AnalysisJob).filter(
        AnalysisJob.qa_analysis_id == analysis_id,
        AnalysisJob.job_type == job_type,
    ).update(
        {"status": "completed", "completed_at": datetime.now(timezone.utc)},
        synchronize_session=False,
    )

    # SELECT FOR UPDATE garante que só um worker vence a corrida pra marcar "completed"
    analysis = (
        db.query(QaAnalysis)
        .filter(QaAnalysis.id == analysis_id)
        .with_for_update()
        .first()
    )
    if analysis is None:
        return

    pending_count = (
        db.query(func.count(AnalysisJob.id))
        .filter(
            AnalysisJob.qa_analysis_id == analysis_id,
            AnalysisJob.status.in_(["pending", "running"]),
        )
        .scalar()
    )

    if pending_count == 0:
        analysis.status = "completed"
        logger.info(f"[Jobs] Todos os jobs concluídos | analysis_id={analysis_id}")


def mark_job_error(db, analysis_id: int, job_type: str, error: Exception) -> None:
    db.query(AnalysisJob).filter(
        AnalysisJob.qa_analysis_id == analysis_id,
        AnalysisJob.job_type == job_type,
    ).update(
        {"status": "error", "error_message": str(error)[:2000]},
        synchronize_session=False,
    )

    db.query(QaAnalysis).filter(QaAnalysis.id == analysis_id).update(
        {"status": "error"},
        synchronize_session=False,
    )
