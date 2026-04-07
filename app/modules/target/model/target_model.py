from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.base import Base


class Target(Base):
    __tablename__ = "targets"

    id = Column(Integer, primary_key=True)

    # ----------------------
    # DONO
    # ----------------------
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # owner_type = "user"         → alvo individual, debita BillingAccount do user
    # owner_type = "organization" → alvo da org, debita BillingAccount da org
    owner_type = Column(String(20), default="user", nullable=False)
    owner_id = Column(Integer, nullable=False)  # user.id ou organization.id

    # ----------------------
    # DADOS DE EXECUÇÃO
    # ----------------------
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)  # objetivo do QA

    # Descrições geradas pelo BrowserUse (contexto de execução)
    tests_description = Column(Text, nullable=True)
    playwright_description = Column(Text, nullable=True)

    # draft | generating | processing | completed | error
    status = Column(String(50), nullable=False, default="draft")

    deleted_at = Column(DateTime, nullable=True, default=None)

    # ----------------------
    # RELACIONAMENTOS
    # ----------------------
    user = relationship("User", back_populates="targets")

    organization = relationship(
        "Organization",
        primaryjoin="and_(foreign(Target.owner_id) == Organization.id, Target.owner_type == 'organization')",
        back_populates="targets",
        viewonly=True,
    )

    # Telas associadas (many-to-many via target_screens)
    screens = relationship(
        "Screen",
        secondary="target_screens",
        back_populates="targets",
        lazy="selectin",
    )

    test_cases = relationship(
        "TestCase",
        back_populates="target",
        cascade="all, delete-orphan",
    )

    playwright_scripts = relationship(
        "PlaywrightScript",
        back_populates="target",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    jobs = relationship(
        "TargetJob",
        back_populates="target",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
