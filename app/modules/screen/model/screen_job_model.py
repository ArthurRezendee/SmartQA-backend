from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base


class ScreenJob(Base):
    __tablename__ = "screen_jobs"

    id = Column(Integer, primary_key=True)

    screen_id = Column(
        Integer,
        ForeignKey("screens.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "documentation"
    job_type = Column(String(50), nullable=False)

    # "pending" | "running" | "completed" | "error"
    status = Column(String(20), nullable=False, default="pending")

    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    screen = relationship("Screen", back_populates="jobs")
