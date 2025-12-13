from app.shared.controller import BaseController
from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService
from fastapi import HTTPException


class QaAnalysisController(BaseController):

    def __init__(self):
        self.service = QaAnalysisService()

    async def list_qa_analysis(self, db):
        return await self.service.list(db)

    async def get_qa_analysis(self, db, entity_id: int):
        return await self.service.get_or_fail(db, entity_id)

    async def create_qa_analysis(self, db, data: dict, documents: list):
        try:
            return await self.service.create_with_documents(db, data, documents)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    async def update_qa_analysis(self, db, entity_id: int, data):
        return await self.service.update(db, entity_id, data.dict(exclude_unset=True))

    async def delete_qa_analysis(self, db, entity_id: int):
        return await self.service.delete(db, entity_id)
