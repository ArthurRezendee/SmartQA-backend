from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base


class StressTest(Base):
    __tablename__ = "stress_tests"

    id = Column(Integer, primary_key=True, index=True)

    target_id = Column(Integer, ForeignKey("targets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner_type = Column(String(20), nullable=False, default="user")
    owner_id = Column(Integer, nullable=False)

    # pending | running | completed | error
    status = Column(String(20), nullable=False, default="pending")

    summary = Column(Text, nullable=True)
    total_findings = Column(Integer, nullable=False, default=0)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    element_map = Column(Text, nullable=True)
    worker_batches = Column(Text, nullable=True)

    deleted_at = Column(DateTime, nullable=True, default=None)

    target = relationship("Target", back_populates="stress_tests")
    findings = relationship(
        "StressTestFinding",
        back_populates="stress_test",
        cascade="all, delete-orphan",
        order_by="StressTestFinding.order_index",
        lazy="selectin",
    )
