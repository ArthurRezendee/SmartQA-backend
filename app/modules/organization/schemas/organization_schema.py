from pydantic import BaseModel
from typing import Optional


class OrganizationCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    avatar_color: Optional[str] = None
    plan_id: int


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_color: Optional[str] = None


class OrganizationMemberAdd(BaseModel):
    user_id: int
    role: str = "member"  # owner | admin | member


class OrganizationMemberUpdate(BaseModel):
    role: str