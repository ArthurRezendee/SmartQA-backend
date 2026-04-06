from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base


class TargetJob(Base):
    __tablename__ = "target_jobs"

    id = Column(Integer, primary_key=True)

    target_id = Column(
        Integer,
        ForeignKey("targets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "test_cases" | "scripts" | "documentation"
    job_type = Column(String(50), nullable=False)

    # "pending" | "running" | "completed" | "error"
    status = Column(String(20), nullable=False, default="pending")

    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    target = relationship("Target", back_populates="jobs")
