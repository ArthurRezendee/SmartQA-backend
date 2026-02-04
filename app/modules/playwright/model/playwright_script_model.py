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


class PlaywrightScript(Base):
    __tablename__ = "playwright_scripts"

    id = Column(Integer, primary_key=True)

    analysis_id = Column(
        Integer,
        ForeignKey("qa_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False, default="Playwright Script")

    version = Column(Integer, nullable=False, default=1)

    language = Column(String(50), nullable=False, default="typescript")  # typescript | javascript

    status = Column(String(50), nullable=False, default="generated")
    # draft | generating | generated | validated | failed | archived

    script = Column(Text, nullable=False)

    generator_model = Column(String(100), nullable=True)  # ex: gpt-5-2
    prompt_hash = Column(String(64), nullable=True)       # sha256 do prompt
    error_message = Column(Text, nullable=True)

    meta = Column(JSON, nullable=True)

    analysis = relationship("QaAnalysis", back_populates="playwright_scripts")

    __table_args__ = (
        UniqueConstraint("analysis_id", "version", name="uq_playwright_scripts_analysis_version"),
        Index("ix_playwright_scripts_analysis_status", "analysis_id", "status"),
    )
