from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.modules.billing.model.billing_account_model import BillingAccount
from app.shared.controller import BaseController
from app.modules.plans.model.plan_model import Plan

class BillingController(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return {
            "status": True,
            "message": "Billing module ready",
            "data": None
        }

    async def create_billing_account(
        self,
        db,
        plan_id: int,
        user_id: int | None = None,
        organization_id: int | None = None,
        stripe_customer_id: str | None = None,
    ):
        """
        Cria uma billing account para user ou organization.
        """

        if not user_id and not organization_id:
            raise ValueError("You must provide user_id or organization_id")

        # 🔎 Verifica se já existe
        stmt = select(BillingAccount).where(
            BillingAccount.owner_user_id == user_id
            if user_id
            else BillingAccount.organization_id == organization_id
        )

        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # 🔎 Busca plano
        plan_stmt = select(Plan).where(Plan.id == plan_id)
        plan_result = await db.execute(plan_stmt)
        plan = plan_result.scalar_one_or_none()

        if not plan:
            raise ValueError("Invalid plan_id")

        now = datetime.utcnow()

        billing_account = BillingAccount(
            type="organization" if organization_id else "individual",
            plan_id=plan.id,
            owner_user_id=user_id,
            organization_id=organization_id,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            analyses_used_current_cycle=0,
            extra_credits=0,
            stripe_customer_id=stripe_customer_id,
            subscription_status="active",  # pode ajustar depois via webhook
            is_active=True,
        )

        db.add(billing_account)

        try:
            await db.commit()
            await db.refresh(billing_account)
        except IntegrityError:
            await db.rollback()
            raise

        return billing_account