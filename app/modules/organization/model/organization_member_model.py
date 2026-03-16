from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.orm import relationship
from app.core.base import Base

class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # owner | admin | member
    role = Column(String(50), default="member", nullable=False)

    # Para convites futuros
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    accepted_at = Column(DateTime, nullable=True)

    # ----------------------
    # RELACIONAMENTOS
    # ----------------------
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="organization_memberships")
    invited_by = relationship("User", foreign_keys=[invited_by_id])