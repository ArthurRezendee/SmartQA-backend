from pydantic import BaseModel, HttpUrl


class QaAnalysisCreate(BaseModel):
    name: str
    user_id: int
    target_url: HttpUrl
    description: str | None = None


class QaAnalysisUpdate(BaseModel):
    name: str | None = None
    target_url: HttpUrl | None = None
    description: str | None = None
    status: str | None = None


class QaAnalysisResponse(BaseModel):
    id: int
    name: str
    target_url: str
    description: str | None
    status: str

    class Config:
        from_attributes = True
