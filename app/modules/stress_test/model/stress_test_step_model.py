from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base


class StressTestStep(Base):
    __tablename__ = "stress_test_steps"

    id = Column(Integer, primary_key=True, index=True)

    stress_test_id = Column(
        Integer,
        ForeignKey("stress_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_id = Column(Integer, nullable=False, default=0)

    element_label = Column(String(255), nullable=False)
    element_kind = Column(String(50), nullable=True)
    field_type = Column(String(50), nullable=True)
    attack_key = Column(String(50), nullable=True)
    attack_description = Column(Text, nullable=True)

    # ok | bug | skipped
    result = Column(String(20), nullable=False, default="ok")

    finding_id = Column(
        Integer,
        ForeignKey("stress_test_findings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    finding = relationship("StressTestFinding", back_populates="steps")
