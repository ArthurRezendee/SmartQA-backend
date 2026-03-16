from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.controller import BaseController
from app.shared.responses import success, error
from app.modules.plans.model.plan_model import Plan


class PlansController(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return success("Plans module ready", None)

    async def list_plans(self, db: AsyncSession, scope: str | None = None):
        try:
            query = select(Plan).where(Plan.is_active == True, Plan.is_public == True)

            if scope:
                query = query.where(Plan.scope == scope)

            query = query.order_by(Plan.display_order)

            result = await db.execute(query)
            plans = result.scalars().all()

            data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "slug": p.slug,
                    "description": p.description,
                    "scope": p.scope,
                    "analyses_per_month": p.analyses_per_month,
                    "max_users": p.max_users,
                    "price_cents": p.price_cents,
                    "currency": p.currency,
                    "is_popular": p.is_popular,
                    "is_highlighted": p.is_highlighted,
                    "badge_text": p.badge_text,
                    "button_text": p.button_text,
                    "icon": p.icon,
                    "color": p.color,
                    "display_order": p.display_order,
                }
                for p in plans
            ]

            return success("Planos recuperados", data)

        except Exception as e:
            return error(f"Erro ao buscar planos: {str(e)}")

    async def get_plan(self, db: AsyncSession, plan_id: int):
        try:
            result = await db.execute(
                select(Plan).where(Plan.id == plan_id, Plan.is_active == True)
            )
            plan = result.scalar_one_or_none()

            if not plan:
                return error("Plano não encontrado", status_code=404)

            return success("Plano recuperado", {
                "id": plan.id,
                "name": plan.name,
                "slug": plan.slug,
                "description": plan.description,
                "scope": plan.scope,
                "analyses_per_month": plan.analyses_per_month,
                "max_users": plan.max_users,
                "price_cents": plan.price_cents,
                "currency": plan.currency,
                "is_popular": plan.is_popular,
                "is_highlighted": plan.is_highlighted,
                "badge_text": plan.badge_text,
                "button_text": plan.button_text,
                "icon": plan.icon,
                "color": plan.color,
                "display_order": plan.display_order,
            })

        except Exception as e:
            return error(f"Erro ao buscar plano: {str(e)}")