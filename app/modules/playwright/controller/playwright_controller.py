
from app.shared.controller import BaseController


class PlaywrightController(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return {
            "status": True,
            "message": "Playwright module ready",
            "data": None
        }
