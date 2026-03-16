from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.core.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    avatar_color = Column(String(50), nullable=True)
    avatar_url = Column(Text, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_organizations")

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")

    billing_account = relationship(
        "BillingAccount",
        back_populates="organization",
        uselist=False,
        primaryjoin="Organization.id == foreign(BillingAccount.organization_id)",
    )

    analyses = relationship(
        "QaAnalysis",
        primaryjoin="and_(foreign(QaAnalysis.owner_id) == Organization.id, QaAnalysis.owner_type == 'organization')",
        back_populates="organization",
        viewonly=True,
    )