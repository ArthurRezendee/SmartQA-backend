from pydantic import BaseModel
from typing import Optional, List


class TargetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    screen_ids: List[int] = []
    organization_id: Optional[int] = None


class TargetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tests_description: Optional[str] = None
    playwright_description: Optional[str] = None
    status: Optional[str] = None


class TargetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    tests_description: Optional[str]
    playwright_description: Optional[str]
    status: str
    owner_type: str
    owner_id: int

    class Config:
        from_attributes = True
