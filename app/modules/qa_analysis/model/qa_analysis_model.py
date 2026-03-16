from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base import Base

class QaAnalysis(Base):
    __tablename__ = "qa_analyses"

    id = Column(Integer, primary_key=True)

    # ----------------------
    # DONO (mantido para compatibilidade)
    # ----------------------
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # quem criou

    # Dono efetivo da análise (para billing e permissões)
    # owner_type = "user" → análise individual, debita BillingAccount do user
    # owner_type = "organization" → análise da org, debita BillingAccount da org
    owner_type = Column(String(20), default="user", nullable=False)
    owner_id = Column(Integer, nullable=False)  # user.id ou organization.id

    # ----------------------
    # DADOS
    # ----------------------
    name = Column(String(255), nullable=False)
    target_url = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    screen_context = Column(Text, nullable=True)

    tests_description = Column(Text, nullable=True)
    playwright_description = Column(Text, nullable=True)
    documentation_description = Column(Text, nullable=True)
    uiux_description = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, default="draft")

    # ----------------------
    # RELACIONAMENTOS
    # ----------------------
    user = relationship("User", back_populates="analyses")

    organization = relationship(
        "Organization",
        primaryjoin="and_(foreign(QaAnalysis.owner_id) == Organization.id, QaAnalysis.owner_type == 'organization')",
        back_populates="analyses",
        viewonly=True,
    )

    documents = relationship(
        "QaDocument",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )

    access_credentials = relationship(
        "AccessCredential",
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    test_cases = relationship(
        "TestCase",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )

    playwright_scripts = relationship(
        "PlaywrightScript",
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    documentations = relationship(
        "Documentation",
        back_populates="qa_analysis",
        cascade="all, delete-orphan",
    )