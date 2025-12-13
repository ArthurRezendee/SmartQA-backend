from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
)
from app.core.base import Base

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

    role = Column(String(50), default="user", nullable=False)

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"
