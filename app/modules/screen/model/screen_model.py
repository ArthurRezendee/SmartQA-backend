from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.base import Base


class Screen(Base):
    __tablename__ = "screens"

    id = Column(Integer, primary_key=True)

    # ----------------------
    # DONO
    # ----------------------
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # owner_type = "user"         → tela individual
    # owner_type = "organization" → tela da organização
    owner_type = Column(String(20), default="user", nullable=False)
    owner_id = Column(Integer, nullable=False)  # user.id ou organization.id

    # ----------------------
    # DADOS DA TELA
    # ----------------------
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    # Contexto manual fornecido pelo QA
    screen_context = Column(Text, nullable=True)

    # Descrições geradas pelo BrowserUse (conhecimento da tela)
    documentation_description = Column(Text, nullable=True)
    uiux_description = Column(Text, nullable=True)

    # draft | active | archived
    status = Column(String(50), nullable=False, default="draft")

    deleted_at = Column(DateTime, nullable=True, default=None)

    # ----------------------
    # RELACIONAMENTOS
    # ----------------------
    user = relationship("User", back_populates="screens")

    organization = relationship(
        "Organization",
        primaryjoin="and_(foreign(Screen.owner_id) == Organization.id, Screen.owner_type == 'organization')",
        back_populates="screens",
        viewonly=True,
    )

    documents = relationship(
        "ScreenDocument",
        back_populates="screen",
        cascade="all, delete-orphan",
    )

    documentations = relationship(
        "Documentation",
        back_populates="screen",
        cascade="all, delete-orphan",
    )

    access_credentials = relationship(
        "AccessCredential",
        back_populates="screen",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Alvos que referenciam esta tela (many-to-many via target_screens)
    targets = relationship(
        "Target",
        secondary="target_screens",
        back_populates="screens",
        viewonly=True,
    )
