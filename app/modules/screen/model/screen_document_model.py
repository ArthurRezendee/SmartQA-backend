from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base


class ScreenDocument(Base):
    __tablename__ = "screen_documents"

    id = Column(Integer, primary_key=True)

    screen_id = Column(Integer, ForeignKey("screens.id"), nullable=False)

    type = Column(String(50), nullable=False)
    path = Column(Text, nullable=False)

    screen = relationship("Screen", back_populates="documents")
