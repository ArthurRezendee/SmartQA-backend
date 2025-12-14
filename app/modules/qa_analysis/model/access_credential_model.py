from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.core.base import Base


class AccessCredential(Base):
    __tablename__ = "access_credentials"

    id = Column(Integer, primary_key=True)

    qa_analysis_id = Column(
        Integer,
        ForeignKey("qa_analyses.id", ondelete="CASCADE"),
        nullable=False
    )

    field_name = Column(String(100), nullable=False)

    value = Column(String(255), nullable=False)

    analysis = relationship(
        "QaAnalysis",
        back_populates="access_credentials"
    )
