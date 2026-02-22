from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.core.base import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)

    # ----------------------
    # IDENTIDADE
    # ----------------------
    name = Column(String(100), nullable=False)       # "Starter"
    slug = Column(String(100), unique=True, nullable=False)  # "starter"
    description = Column(Text, nullable=True)       # Texto curto do plano

    # ----------------------
    # LIMITES (regra de negócio)
    # ----------------------
    analyses_per_month = Column(Integer, nullable=False)
    max_users = Column(Integer, default=1)

    # ----------------------
    # PREÇO
    # ----------------------
    price_cents = Column(Integer, nullable=False)
    currency = Column(String(10), default="BRL")

    # Stripe
    stripe_price_id = Column(String(255), nullable=True)

    # ----------------------
    # CONTROLE VISUAL
    # ----------------------
    is_popular = Column(Boolean, default=False)     # badge "Mais popular"
    is_highlighted = Column(Boolean, default=False) # destaque visual
    display_order = Column(Integer, default=0)      # ordem na tela

    button_text = Column(String(100), default="Assinar")
    badge_text = Column(String(100), nullable=True) # Ex: "Recomendado"

    color = Column(String(50), nullable=True)       # Ex: "purple", "blue"
    icon = Column(String(100), nullable=True)       # nome do ícone no frontend

    # ----------------------
    # CONTROLE INTERNO
    # ----------------------
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=True)

    # ----------------------
    # RELACIONAMENTO
    # ----------------------
    billing_accounts = relationship("BillingAccount", back_populates="plan")