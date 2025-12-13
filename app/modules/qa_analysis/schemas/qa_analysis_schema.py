
from pydantic import BaseModel


class QaAnalysisBase(BaseModel):
    name: str


class QaAnalysisCreate(QaAnalysisBase):
    pass


class QaAnalysisUpdate(QaAnalysisBase):
    pass


class QaAnalysisResponse(QaAnalysisBase):
    id: int

    class Config:
        from_attributes = True
