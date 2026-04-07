from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.celery_app import celery_app
from app.modules.target.model.target_model import Target
from app.modules.target.model.target_job_model import TargetJob
from app.modules.screen.model.screen_model import Screen
from app.modules.screen.model.screen_job_model import ScreenJob


class AiService:

    async def _register_job(
        self,
        db: AsyncSession,
        target_id: int,
        user_id: int,
        job_type: str,
        celery_task_name: str,
    ) -> dict:
        result = await db.execute(
            select(Target).where(
                Target.id == target_id,
                Target.user_id == user_id,
            )
        )
        target = result.scalar_one_or_none()
        if target is None:
            raise ValueError(f"Alvo {target_id} não encontrado")

        await db.execute(
            delete(TargetJob).where(
                TargetJob.target_id == target_id,
                TargetJob.job_type == job_type,
            )
        )
        db.add(TargetJob(target_id=target_id, job_type=job_type, status="pending"))
        target.status = "processing"
        await db.commit()

        celery_app.send_task(celery_task_name, kwargs={"analysis_id": target_id, "user_id": user_id})

        return {"status": "processing", "target_id": target_id}

    async def generate_test_cases(self, db: AsyncSession, target_id: int, user_id: int):
        return await self._register_job(db, target_id, user_id, "test_cases", "jobs.ia.generate_test_case")

    async def generate_scripts_playwright(self, db: AsyncSession, target_id: int, user_id: int):
        return await self._register_job(db, target_id, user_id, "scripts", "jobs.ia.generate_scripts_playwright")

    async def generate_documentation_for_screen(self, db: AsyncSession, screen_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(Screen).where(
                Screen.id == screen_id,
                Screen.user_id == user_id,
            )
        )
        screen = result.scalar_one_or_none()
        if screen is None:
            raise ValueError(f"Tela {screen_id} não encontrada")

        await db.execute(
            delete(ScreenJob).where(
                ScreenJob.screen_id == screen_id,
                ScreenJob.job_type == "documentation",
            )
        )
        db.add(ScreenJob(screen_id=screen_id, job_type="documentation", status="pending"))
        await db.commit()

        celery_app.send_task(
            "jobs.ia.generate_documentation",
            kwargs={"screen_id": screen_id, "user_id": user_id},
        )

        return {"status": "pending", "screen_id": screen_id}

    async def get_screen_doc_status(self, db: AsyncSession, screen_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(Screen).where(
                Screen.id == screen_id,
                Screen.user_id == user_id,
            )
        )
        screen = result.scalar_one_or_none()
        if screen is None:
            raise ValueError(f"Tela {screen_id} não encontrada")

        job_result = await db.execute(
            select(ScreenJob).where(
                ScreenJob.screen_id == screen_id,
                ScreenJob.job_type == "documentation",
            )
        )
        job = job_result.scalar_one_or_none()

        if job is None:
            return {
                "screen_id": screen_id,
                "status": "not_requested",
                "job": None,
            }

        return {
            "screen_id": screen_id,
            "status": job.status,
            "job": {
                "job_type": job.job_type,
                "status": job.status,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message,
            },
        }

    async def get_target_jobs(self, db: AsyncSession, target_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(Target).where(
                Target.id == target_id,
                Target.user_id == user_id,
            )
        )
        target = result.scalar_one_or_none()
        if target is None:
            raise ValueError(f"Alvo {target_id} não encontrado")

        jobs_result = await db.execute(
            select(TargetJob)
            .where(TargetJob.target_id == target_id)
            .order_by(TargetJob.created_at)
        )
        jobs = jobs_result.scalars().all()

        return {
            "target_id": target_id,
            "status": target.status,
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

    async def analyze_target(self, target_id: int, user_id: int, requirements: list[str]):
        celery_app.send_task(
            "jobs.ia.generate_screen_description",
            kwargs={
                "analysis_id": target_id,
                "user_id": user_id,
                "requirements": requirements if requirements else None,
            },
        )

        return {
            "status": "processing",
            "target_id": target_id,
            "queued": [r for r in (requirements or ["test_cases", "scripts"]) if r in ("test_cases", "scripts")],
        }
