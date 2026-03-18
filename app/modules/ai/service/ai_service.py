from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.celery_app import celery_app
from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from app.modules.qa_analysis.model.analysis_job_model import AnalysisJob


class AiService:

    async def _register_job(
        self,
        db: AsyncSession,
        analysis_id: int,
        user_id: int,
        job_type: str,
        celery_task_name: str,
    ) -> dict:
        result = await db.execute(
            select(QaAnalysis).where(
                QaAnalysis.id == analysis_id,
                QaAnalysis.user_id == user_id,
            )
        )
        analysis = result.scalar_one_or_none()
        if analysis is None:
            raise ValueError(f"Análise {analysis_id} não encontrada")

        # Recria o job (remove anterior se existir, ex: usuário solicitando novamente)
        await db.execute(
            delete(AnalysisJob).where(
                AnalysisJob.qa_analysis_id == analysis_id,
                AnalysisJob.job_type == job_type,
            )
        )
        db.add(AnalysisJob(qa_analysis_id=analysis_id, job_type=job_type, status="pending"))
        analysis.status = "processing"
        await db.commit()

        celery_app.send_task(celery_task_name, kwargs={"analysis_id": analysis_id, "user_id": user_id})

        return {"status": "processing", "analysis_id": analysis_id}

    async def generate_test_cases(self, db: AsyncSession, analysis_id: int, user_id: int):
        return await self._register_job(db, analysis_id, user_id, "test_cases", "jobs.ia.generate_test_case")

    async def generate_scripts_playwright(self, db: AsyncSession, analysis_id: int, user_id: int):
        return await self._register_job(db, analysis_id, user_id, "scripts", "jobs.ia.generate_scripts_playwright")

    async def generate_documentation(self, db: AsyncSession, analysis_id: int, user_id: int):
        return await self._register_job(db, analysis_id, user_id, "documentation", "jobs.ia.generate_documentation")


    async def get_analysis_jobs(self, db: AsyncSession, analysis_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(QaAnalysis).where(
                QaAnalysis.id == analysis_id,
                QaAnalysis.user_id == user_id,
            )
        )
        analysis = result.scalar_one_or_none()
        if analysis is None:
            raise ValueError(f"Análise {analysis_id} não encontrada")

        jobs_result = await db.execute(
            select(AnalysisJob)
            .where(AnalysisJob.qa_analysis_id == analysis_id)
            .order_by(AnalysisJob.created_at)
        )
        jobs = jobs_result.scalars().all()

        return {
            "analysis_id": analysis_id,
            "status": analysis.status,
            "jobs": [
                {
                    "job_type": j.job_type,
                    "status": j.status,
                    "started_at": j.started_at,
                    "completed_at": j.completed_at,
                    "error_message": j.error_message,
                }
                for j in jobs
            ],
        }

    async def analyze_target(self, analysis_id: int, user_id: int, requirements: list[str]):
        celery_app.send_task(
            "jobs.ia.generate_screen_description",
            kwargs={
                "analysis_id": analysis_id,
                "user_id": user_id,
                "requirements": requirements if requirements else None
            }
        )

        return {
            "status": "processing",
            "analysis_id": analysis_id,
            "queued": requirements if requirements else ["test_cases", "scripts", "documentation"]
        }