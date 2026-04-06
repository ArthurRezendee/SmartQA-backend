from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base


class AccessCredential(Base):
    __tablename__ = "access_credentials"

    id = Column(Integer, primary_key=True)

    screen_id = Column(
        Integer,
        ForeignKey("screens.id", ondelete="CASCADE"),
        nullable=False,
    )

    field_name = Column(String(100), nullable=False)
    value = Column(String(255), nullable=False)

    screen = relationship("Screen", back_populates="access_credentials")
