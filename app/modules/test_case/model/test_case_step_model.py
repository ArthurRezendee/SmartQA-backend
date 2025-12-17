from sqlalchemy import (
    Column,
    Integer,
    Text,
    Enum,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.core.base import Base


class TestCaseStep(Base):
    __tablename__ = "test_case_steps"

    id = Column(Integer, primary_key=True)

    test_case_id = Column(
        Integer,
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    order = Column(Integer, nullable=False)

    action = Column(Text, nullable=False)
    expected_result = Column(Text, nullable=False)

    step_type = Column(
        Enum(
            "action",
            "assertion",
            "setup",
            name="test_step_type_enum",
        ),
        nullable=False,
        default="action",
    )

    test_case = relationship("TestCase", back_populates="steps")
