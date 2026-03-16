
from app.shared.controller import BaseController


class OrganizationController(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return {
            "status": True,
            "message": "Organization module ready",
            "data": None
        }
