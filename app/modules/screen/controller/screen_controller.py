from app.modules.screen.service.screen_service import ScreenService


class ScreenController:

    def __init__(self):
        self.service = ScreenService()

    async def list_screens(self, db, user_id: int, owner_type: str, owner_id: int):
        return await self.service.list_by_owner(db, user_id, owner_type, owner_id)

    async def get_screen(self, db, screen_id: int, user_id: int):
        return await self.service.get_or_fail(db, screen_id, user_id)

    async def create_screen(self, db, data: dict, documents: list, access_credentials: list | None = None):
        return await self.service.create_with_documents(db, data, documents, access_credentials)

    async def update_screen(self, db, screen_id: int, data: dict, user_id: int):
        return await self.service.update(db, screen_id, data, user_id)

    async def delete_screen(self, db, screen_id: int, user_id: int):
        return await self.service.delete(db, screen_id, user_id)
