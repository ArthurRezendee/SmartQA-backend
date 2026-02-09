
from app.shared.controller import BaseController


class DocumentationsController(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return {
            "status": True,
            "message": "Documentations module ready",
            "data": None
        }
