from app.shared.controller import BaseController
from app.modules.ai.service.ai_service import AiService


class AiController(BaseController):

    def __init__(self):
        self.service = AiService()

    async def generate_test_cases(self, analysis_id: int, user_id: int):
        return await self.service.generate_test_cases(
            analysis_id=analysis_id,
            user_id=user_id
        )
        
    async def generate_scripts_playwright(self, analysis_id: int, user_id: int):
        return await self.service.generate_scripts_playwright(
            analysis_id=analysis_id,
            user_id=user_id
        )
        
    async def generate_documentation(self, analysis_id: int, user_id: int):
        return await self.service.generate_documentation(
            analysis_id=analysis_id,
            user_id=user_id
        )
