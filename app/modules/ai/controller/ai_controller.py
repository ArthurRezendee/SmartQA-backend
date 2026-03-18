from app.shared.controller import BaseController
from app.modules.ai.service.ai_service import AiService


class AiController(BaseController):

    def __init__(self):
        self.service = AiService()
        
    async def analyze_target(self, analysis_id: int, user_id: int, requirements: list[str]):
        return await self.service.analyze_target(
            analysis_id=analysis_id,
            user_id=user_id,
            requirements=requirements
        )

    async def generate_test_cases(self, db, analysis_id: int, user_id: int):
        return await self.service.generate_test_cases(
            db=db, analysis_id=analysis_id, user_id=user_id
        )

    async def generate_scripts_playwright(self, db, analysis_id: int, user_id: int):
        return await self.service.generate_scripts_playwright(
            db=db, analysis_id=analysis_id, user_id=user_id
        )

    async def generate_documentation(self, db, analysis_id: int, user_id: int):
        return await self.service.generate_documentation(
            db=db, analysis_id=analysis_id, user_id=user_id
        )

    async def get_analysis_jobs(self, db, analysis_id: int, user_id: int):
        return await self.service.get_analysis_jobs(
            db=db,
            analysis_id=analysis_id,
            user_id=user_id,
        )