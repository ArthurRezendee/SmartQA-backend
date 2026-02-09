from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    JSON,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import relationship

from app.core.base import Base


class Documentation(Base):
    __tablename__ = "documentations"

    id = Column(Integer, primary_key=True)

    qa_analysis_id = Column(
        Integer,
        ForeignKey("qa_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Metadados
    title = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, default=1)

    status = Column(
        String(50),
        nullable=False,
        default="generated",
    )
    # draft | generating | generated | reviewed | approved | failed | archived

    # Conteúdo
    content = Column(Text, nullable=False)
    content_format = Column(
        String(50),
        nullable=False,
        default="text",
    )
    # text | markdown | html

    # Origem / IA
    generated_by = Column(
        String(50),
        nullable=False,
        default="ai",
    )
    # ai | human | hybrid

    generator_model = Column(String(100), nullable=True)
    prompt_hash = Column(String(64), nullable=True)

    # Erros / observações
    error_message = Column(Text, nullable=True)

    # Campo flexível
    meta = Column(JSON, nullable=True)

    qa_analysis = relationship(
        "QaAnalysis",
        back_populates="documentations",
    )

    __table_args__ = (
        UniqueConstraint(
            "qa_analysis_id",
            "version",
            name="uq_documentations_analysis_version",
        ),
        Index(
            "ix_documentations_analysis_status",
            "qa_analysis_id",
            "status",
        ),
    )
