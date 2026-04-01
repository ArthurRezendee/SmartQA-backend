from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id = Column(Integer, primary_key=True, index=True)

    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    invited_email = Column(String(255), nullable=False, index=True)
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # owner | admin | member
    role = Column(String(50), default="member", nullable=False)

    # Token único para aceitar/recusar via link
    token = Column(String(64), unique=True, index=True, nullable=False)

    # pending | accepted | declined | expired
    status = Column(String(50), default="pending", nullable=False)

    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Preenchido quando o usuário convidado existe ou se cadastra
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ─── RELACIONAMENTOS ────────────────────────────────────────────────────
    organization = relationship("Organization")
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    user = relationship("User", foreign_keys=[user_id])
