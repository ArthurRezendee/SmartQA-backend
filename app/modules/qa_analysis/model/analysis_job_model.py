from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True)
    qa_analysis_id = Column(Integer, ForeignKey("qa_analyses.id", ondelete="CASCADE"), nullable=False)

    # "test_cases" | "scripts" | "documentation"
    job_type = Column(String(50), nullable=False)

    # "pending" | "running" | "completed" | "error"
    status = Column(String(20), nullable=False, default="pending")

    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    analysis = relationship("QaAnalysis", back_populates="jobs")
