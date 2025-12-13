from app.shared.controller import BaseController
from app.modules.user.service.user_service import UserService

class UserController(BaseController):
    
    def __init__(self):
        self.service = UserService()

    async def index(self):
        return {
            "status": True,
            "message": "User module ready",
            "data": None
        }

    async def list_users(self, db):
        return await self.service.list(db)

    async def get_user(self, db, entity_id: int):
        return await self.service.get(db, entity_id)

    async def create_user(self, db, data):
        return await self.service.create(db, data.dict())

    async def update_user(self, db, entity_id: int, data):
        return await self.service.update(db, entity_id, data.dict())

    async def delete_user(self, db, entity_id: int):
        return await self.service.delete(db, entity_id)
