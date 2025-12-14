from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService


class QaAnalysisController:

    def __init__(self):
        self.service = QaAnalysisService()

    async def list_qa_analysis(self, db, user_id: int):
        return await self.service.list_by_user(db, user_id)

    async def get_qa_analysis(self, db, entity_id: int, user_id: int):
        return await self.service.get_or_fail(db, entity_id, user_id)

    async def create_qa_analysis(
        self,
        db,
        data: dict,
        documents: list,
        access_credentials: list | None = None
    ):
        return await self.service.create_with_documents(
            db,
            data,
            documents,
            access_credentials
        )

    async def update_qa_analysis(self, db, entity_id: int, data, user_id: int):
        return await self.service.update(db, entity_id, data.dict(), user_id)

    async def delete_qa_analysis(self, db, entity_id: int, user_id: int):
        return await self.service.delete(db, entity_id, user_id)
