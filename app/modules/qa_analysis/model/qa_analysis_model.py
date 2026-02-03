from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base

class QaAnalysis(Base):
    __tablename__ = "qa_analyses"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(255), nullable=False)
    target_url = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    screen_context = Column(Text, nullable=True)

    tests_description = Column(Text, nullable=True)          
    playwright_description = Column(Text, nullable=True)      
    documentation_description = Column(Text, nullable=True)  
    uiux_description = Column(Text, nullable=True)            

    status = Column(String(50), nullable=False, default="draft")

    documents = relationship(
        "QaDocument",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )

    access_credentials = relationship(
        "AccessCredential",
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    test_cases = relationship(
        "TestCase",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )
