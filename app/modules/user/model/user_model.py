from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
)
from app.core.base import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)

    password_hash = Column(String(255), nullable=True)

    google_id = Column(String(255), unique=True, index=True, nullable=True)
    avatar_url = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    email_verification_code = Column(String(6), nullable=True)
    email_verification_expires_at = Column(DateTime(timezone=True), nullable=True)

    role = Column(String(50), default="user", nullable=False)
    
    owned_organizations = relationship("Organization", foreign_keys="Organization.owner_id", back_populates="owner")
    organization_memberships = relationship("OrganizationMember", foreign_keys="OrganizationMember.user_id", back_populates="user")
    
    analyses = relationship("QaAnalysis", back_populates="user", foreign_keys="QaAnalysis.user_id")


    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"
