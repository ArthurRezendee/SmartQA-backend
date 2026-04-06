from app.shared.controller import BaseController
from app.modules.ai.service.ai_service import AiService


class AiController(BaseController):

    def __init__(self):
        self.service = AiService()

    async def analyze_target(self, target_id: int, user_id: int, requirements: list[str]):
        return await self.service.analyze_target(
            target_id=target_id,
            user_id=user_id,
            requirements=requirements,
        )

    async def generate_test_cases(self, db, target_id: int, user_id: int):
        return await self.service.generate_test_cases(
            db=db, target_id=target_id, user_id=user_id
        )

    async def generate_scripts_playwright(self, db, target_id: int, user_id: int):
        return await self.service.generate_scripts_playwright(
            db=db, target_id=target_id, user_id=user_id
        )

    async def generate_documentation_for_screen(self, db, screen_id: int, user_id: int):
        return await self.service.generate_documentation_for_screen(
            db=db, screen_id=screen_id, user_id=user_id
        )

    async def get_target_jobs(self, db, target_id: int, user_id: int):
        return await self.service.get_target_jobs(
            db=db,
            target_id=target_id,
            user_id=user_id,
        )
