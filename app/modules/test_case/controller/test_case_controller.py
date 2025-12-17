
from app.shared.controller import BaseController


class TestCaseController(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return {
            "status": True,
            "message": "TestCase module ready",
            "data": None
        }
