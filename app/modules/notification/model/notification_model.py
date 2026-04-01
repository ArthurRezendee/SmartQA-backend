from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Tipo da notificação — ex: "organization_invite"
    type = Column(String(100), nullable=False)

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)

    is_read = Column(Boolean, default=False, nullable=False)

    # Dados extras estruturados — varia por tipo de notificação
    # Para "organization_invite":
    # {
    #   "invitation_id": int,
    #   "organization_id": int,
    #   "organization_name": str,
    #   "organization_slug": str,
    #   "token": str,          ← token para aceitar/recusar via API
    #   "role": str,
    #   "inviter_name": str
    # }
    payload = Column(JSON, nullable=True)

    # ─── RELACIONAMENTOS ────────────────────────────────────────────────────
    user = relationship("User")
