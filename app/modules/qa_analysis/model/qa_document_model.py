from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base


class QaDocument(Base):
    __tablename__ = "qa_documents"

    id = Column(Integer, primary_key=True)

    qa_analysis_id = Column(Integer, ForeignKey("qa_analyses.id"), nullable=False)

    type = Column(String(50), nullable=False)  
    path = Column(Text, nullable=False)

    analysis = relationship("QaAnalysis", back_populates="documents")
