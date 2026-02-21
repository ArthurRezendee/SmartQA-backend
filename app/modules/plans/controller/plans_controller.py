
from app.shared.controller import BaseController


class PlansController(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return {
            "status": True,
            "message": "Plans module ready",
            "data": None
        }
