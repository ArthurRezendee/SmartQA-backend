from fastapi import HTTPException
from app.shared.controller import BaseController
from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService


class QaAnalysisController(BaseController):

    def __init__(self):
        self.service = QaAnalysisService()

    async def list_qa_analysis(self, db, user_id: int):
        return await self.service.list_by_user(db, user_id)

    async def get_qa_analysis(self, db, entity_id: int, user_id: int):
        return await self.service.get_or_fail(db, entity_id, user_id)

    async def create_qa_analysis(self, db, data: dict, documents: list):
        try:
            return await self.service.create_with_documents(db, data, documents)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def update_qa_analysis(self, db, entity_id: int, data, user_id: int):
        return await self.service.update(db, entity_id, data.dict(exclude_unset=True), user_id)

    async def delete_qa_analysis(self, db, entity_id: int, user_id: int):
        return await self.service.delete(db, entity_id, user_id)
