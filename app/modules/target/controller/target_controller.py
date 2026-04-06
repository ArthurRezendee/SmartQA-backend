from app.modules.target.service.target_service import TargetService


class TargetController:

    def __init__(self):
        self.service = TargetService()

    async def list_targets(self, db, user_id: int, owner_type: str, owner_id: int):
        return await self.service.list_by_owner(db, user_id, owner_type, owner_id)

    async def get_target(self, db, target_id: int, user_id: int):
        return await self.service.get_or_fail(db, target_id, user_id)

    async def create_target(self, db, data: dict, screen_ids: list):
        return await self.service.create(db, data, screen_ids)

    async def update_target(self, db, target_id: int, data: dict, user_id: int):
        return await self.service.update(db, target_id, data, user_id)

    async def delete_target(self, db, target_id: int, user_id: int):
        return await self.service.delete(db, target_id, user_id)
