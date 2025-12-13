
from pydantic import BaseModel


class QaDocumentBase(BaseModel):
    name: str


class QaDocumentCreate(QaDocumentBase):
    pass


class QaDocumentUpdate(QaDocumentBase):
    pass


class QaDocumentResponse(QaDocumentBase):
    id: int

    class Config:
        from_attributes = True
