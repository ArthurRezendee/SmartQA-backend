from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.core.base import Base

class BillingAccount(Base):
    __tablename__ = "billing_accounts"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), default="individual")  # individual | organization

    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)

    # Se for individual
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Se for organization (futuro)
    organization_id = Column(Integer, nullable=True)

    plan = relationship("Plan", back_populates="billing_accounts")

    # ---- Controle de ciclo ----
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)

    # ---- Controle de uso ----
    analyses_used_current_cycle = Column(Integer, default=0)
    extra_credits = Column(Integer, default=0)

    # ---- Stripe ----
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), nullable=True)
    # active | past_due | canceled | incomplete

    # ---- Controle interno ----
    is_active = Column(Boolean, default=True)
    cancel_at_period_end = Column(Boolean, default=False)
