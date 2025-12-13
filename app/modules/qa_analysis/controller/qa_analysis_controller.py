
from app.shared.controller import BaseController
from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService


class QaAnalysisController(BaseController):

    def __init__(self):
        self.service = QaAnalysisService()

    async def index(self):
        return {
            "status": True,
            "message": "QaAnalysis module ready",
            "data": None
        }

    async def list_qa_analysiss(self, db):
        return await self.service.list(db)

    async def get_qa_analysis(self, db, entity_id: int):
        return await self.service.get(db, entity_id)

    async def create_qa_analysis(self, db, data):
        return await self.service.create(db, data.dict())

    async def update_qa_analysis(self, db, entity_id: int, data):
        return await self.service.update(db, entity_id, data.dict())

    async def delete_qa_analysis(self, db, entity_id: int):
        return await self.service.delete(db, entity_id)
