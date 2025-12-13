
from app.shared.controller import BaseController


class UserController(BaseController):

    async def index(self):
        return {
            "status": True,
            "message": "User module ready",
            "data": None
        }
