from pydantic import BaseModel
from typing import Optional, List


class ScreenCreate(BaseModel):
    name: str
    url: Optional[str] = None
    description: Optional[str] = None
    screen_context: Optional[str] = None
    organization_id: Optional[int] = None


class AccessCredentialInput(BaseModel):
    field_name: str
    value: str


class ScreenUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    screen_context: Optional[str] = None
    documentation_description: Optional[str] = None
    uiux_description: Optional[str] = None
    status: Optional[str] = None
    access_credentials: Optional[List[AccessCredentialInput]] = None


class ScreenResponse(BaseModel):
    id: int
    name: str
    url: Optional[str]
    description: Optional[str]
    screen_context: Optional[str]
    documentation_description: Optional[str]
    uiux_description: Optional[str]
    status: str
    owner_type: str
    owner_id: int

    class Config:
        from_attributes = True
