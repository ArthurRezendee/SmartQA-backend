from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base


class StressTestFinding(Base):
    __tablename__ = "stress_test_findings"

    id = Column(Integer, primary_key=True, index=True)

    stress_test_id = Column(
        Integer,
        ForeignKey("stress_tests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order_index = Column(Integer, nullable=False, default=0)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    severity = Column(
        Enum("critical", "high", "medium", "low", name="stress_severity_enum"),
        nullable=False,
        default="medium",
    )

    category = Column(
        Enum("crash", "validation", "ui_error", "http_error", "security", "functional", "ux", name="stress_category_enum"),
        nullable=False,
        default="functional",
    )

    element = Column(Text, nullable=True)
    input_used = Column(Text, nullable=True)
    steps_to_reproduce = Column(Text, nullable=True)  # JSON array serializado
    error_details = Column(Text, nullable=True)
    screenshot_path = Column(String(500), nullable=True)

    stress_test = relationship("StressTest", back_populates="findings")
