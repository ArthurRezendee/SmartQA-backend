from app.core.celery_app import celery_app

class AiService:

    async def generate_test_cases(
        self,
        analysis_id: int,
        user_id: int
    ):
        celery_app.send_task(
            "jobs.ia.generate_screen_description",
            kwargs={
                "analysis_id": analysis_id,
                "user_id": user_id
            }
        )

        return {
            "status": "processing",
            "analysis_id": analysis_id
        }
