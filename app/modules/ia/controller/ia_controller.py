
from app.shared.controller import BaseController


class IaController(BaseController):

    async def index(self):
        return {
            "status": True,
            "message": "Ia module ready",
            "data": None
        }
