from pydantic import BaseModel, EmailStr
from typing import Literal, Optional


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


# ─── Convites ─────────────────────────────────────────────────────────────────

class OrganizationInviteCreate(BaseModel):
    email: EmailStr
    role: str = "member"  # admin | member


class InvitationRespond(BaseModel):
    action: Literal["accept", "decline"]