from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum,
    Boolean,
    Float,
    ForeignKey,
    DateTime
)
from sqlalchemy.orm import relationship

from app.core.base import Base


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True)

    # relacionamento
    qa_analysis_id = Column(
        Integer,
        ForeignKey("qa_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # identidade
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)

    # classificação
    test_type = Column(
        Enum(
            "functional",
            "regression",
            "smoke",
            "exploratory",
            name="test_type_enum",
        ),
        nullable=False,
        default="functional",
    )

    scenario_type = Column(
        Enum(
            "positive",
            "negative",
            "edge",
            name="scenario_type_enum",
        ),
        nullable=False,
        default="positive",
    )

    # prioridade e risco
    priority = Column(
        Enum(
            "low",
            "medium",
            "high",
            "critical",
            name="test_priority_enum",
        ),
        nullable=False,
        default="medium",
    )

    risk_level = Column(
        Enum(
            "low",
            "medium",
            "high",
            name="test_risk_enum",
        ),
        nullable=False,
        default="medium",
    )

    # contexto
    preconditions = Column(Text, nullable=True)
    postconditions = Column(Text, nullable=True)

    # resultado esperado (macro)
    expected_result = Column(Text, nullable=True)

    # ciclo de vida
    status = Column(
        Enum(
            "generated",
            "reviewed",
            "approved",
            "deprecated",
            name="test_case_status_enum",
        ),
        nullable=False,
        default="generated",
    )

    # automação
    has_automation = Column(Boolean, nullable=False, default=False)
    automation_status = Column(
        Enum(
            "not_generated",
            "generated",
            "outdated",
            name="automation_status_enum",
        ),
        nullable=False,
        default="not_generated",
    )

    # metadados de IA
    generated_by_ai = Column(Boolean, nullable=False, default=True)
    ai_model_used = Column(String(100), nullable=True)
    ai_confidence_score = Column(Float, nullable=True)

    deleted_at = Column(DateTime, nullable=True, default=None) 
    # relacionamentos
    steps = relationship(
        "TestCaseStep",
        back_populates="test_case",
        cascade="all, delete-orphan",
        order_by="TestCaseStep.order",
    )

    analysis = relationship("QaAnalysis", back_populates="test_cases")
