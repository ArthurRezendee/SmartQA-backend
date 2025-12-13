
from app.shared.controller import BaseController
from app.modules.qa_analysis.service.qa_document_service import QaDocumentService


class QaDocumentController(BaseController):

    def __init__(self):
        self.service = QaDocumentService()

    async def list_qa_documents(self, db):
        return await self.service.list(db)

    async def get_qa_document(self, db, entity_id: int):
        return await self.service.get(db, entity_id)

    async def create_qa_document(self, db, data):
        return await self.service.create(db, data.dict())

    async def update_qa_document(self, db, entity_id: int, data):
        return await self.service.update(db, entity_id, data.dict())

    async def delete_qa_document(self, db, entity_id: int):
        return await self.service.delete(db, entity_id)
