
from app.shared.controller import BaseController


class EmailController(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return {
            "status": True,
            "message": "Email module ready",
            "data": None
        }
