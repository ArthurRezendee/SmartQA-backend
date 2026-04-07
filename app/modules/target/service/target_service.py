from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.modules.target.model.target_model import Target
from app.modules.target.model.target_screens_model import TargetScreen
from app.modules.screen.model.screen_model import Screen
from app.modules.user.model.user_model import User
from app.modules.billing.model.billing_account_model import BillingAccount
from app.modules.plans.model.plan_model import Plan


class TargetService:

    async def _validate_and_consume_quota(
        self,
        db: AsyncSession,
        user_id: int,
        owner_type: str = "user",
        owner_id: int | None = None,
    ):
        if owner_type == "organization" and owner_id:
            billing_filter = (
                BillingAccount.organization_id == owner_id,
                BillingAccount.is_active == True,
            )
        else:
            billing_filter = (
                BillingAccount.owner_user_id == user_id,
                BillingAccount.is_active == True,
            )

        result = await db.execute(
            select(BillingAccount)
            .options(selectinload(BillingAccount.plan))
            .where(*billing_filter)
        )
        billing = result.scalar_one_or_none()

        if not billing:
            owner_label = "Organização" if owner_type == "organization" else "Usuário"
            raise ValueError(f"{owner_label} sem billing account ativa")

        if billing.subscription_status != "active":
            raise ValueError("Assinatura inativa")

        now = datetime.utcnow()
        if billing.current_period_end and now > billing.current_period_end:
            billing.analyses_used_current_cycle = 0
            billing.current_period_start = now

        plan = billing.plan
        allowed = (
            plan.analyses_per_month
            + billing.extra_credits
            - billing.analyses_used_current_cycle
        )

        if allowed <= 0:
            raise ValueError("Limite mensal de análises atingido")

        billing.analyses_used_current_cycle += 1
        await db.flush()
        return True

    async def list_by_owner(self, db: AsyncSession, user_id: int, owner_type: str, owner_id: int):
        try:
            result = await db.execute(
                select(Target)
                .options(
                    selectinload(Target.screens).selectinload(Screen.access_credentials),
                )
                .where(
                    Target.owner_type == owner_type,
                    Target.owner_id == owner_id,
                    Target.deleted_at.is_(None),
                )
            )
            targets = result.scalars().unique().all()

            return [self._serialize(t) for t in targets]

        except Exception as e:
            raise ValueError(f"Erro ao listar alvos: {str(e)}")

    async def get_or_fail(self, db: AsyncSession, target_id: int, user_id: int):
        try:
            result = await db.execute(
                select(Target)
                .options(
                    selectinload(Target.screens).selectinload(Screen.documents),
                    selectinload(Target.screens).selectinload(Screen.access_credentials),
                )
                .where(Target.id == target_id, Target.user_id == user_id, Target.deleted_at.is_(None))
            )
            target = result.scalar_one_or_none()

            if not target:
                raise ValueError("Alvo não encontrado")

            return self._serialize(target, include_screen_docs=True)

        except Exception as e:
            raise ValueError(str(e))

    def get_or_fail_sync(self, db, target_id: int, user_id: int):
        from sqlalchemy.orm import selectinload as sync_selectinload

        target = (
            db.query(Target)
            .options(
                sync_selectinload(Target.screens).selectinload(Screen.documents),
                sync_selectinload(Target.screens).selectinload(Screen.access_credentials),
            )
            .filter(Target.id == target_id, Target.user_id == user_id, Target.deleted_at.is_(None))
            .first()
        )

        if not target:
            raise ValueError("Alvo não encontrado")

        return self._serialize(target, include_screen_docs=True)

    def _serialize(self, target: Target, include_screen_docs: bool = False) -> dict:
        data = target.to_dict()

        screens_data = []
        for s in (target.screens or []):
            screen_dict = s.to_dict()
            if include_screen_docs:
                screen_dict["documents"] = [
                    {"id": d.id, "type": d.type, "path": d.path}
                    for d in (s.documents or [])
                ]
            screen_dict["access_credentials"] = [
                {"id": c.id, "field_name": c.field_name}
                for c in (s.access_credentials or [])
            ]
            screens_data.append(screen_dict)

        data["screens"] = screens_data
        return data

    async def create(
        self,
        db: AsyncSession,
        data: dict,
        screen_ids: list[int],
    ):
        try:
            result_user = await db.execute(select(User).where(User.id == data["user_id"]))
            if not result_user.scalar_one_or_none():
                raise ValueError("Usuário não encontrado")

            await self._validate_and_consume_quota(
                db,
                user_id=data["user_id"],
                owner_type=data.get("owner_type", "user"),
                owner_id=data.get("owner_id", data["user_id"]),
            )

            target = Target(**data)
            db.add(target)
            await db.flush()

            for screen_id in screen_ids:
                db.add(TargetScreen(target_id=target.id, screen_id=screen_id))

            await db.commit()
            await db.refresh(target)

            result_dict = target.to_dict()
            result_dict["screen_ids"] = screen_ids
            return result_dict

        except IntegrityError:
            await db.rollback()
            raise ValueError("Erro de integridade ao criar alvo")

        except Exception as e:
            await db.rollback()
            raise ValueError(str(e))

    async def update(self, db: AsyncSession, target_id: int, data: dict, user_id: int):
        try:
            result = await db.execute(
                select(Target).where(Target.id == target_id, Target.user_id == user_id)
            )
            target = result.scalar_one_or_none()

            if not target:
                raise ValueError("Alvo não encontrado")

            for field, value in data.items():
                if value is not None and hasattr(target, field):
                    setattr(target, field, value)

            await db.commit()
            await db.refresh(target)
            return target.to_dict()

        except Exception as e:
            await db.rollback()
            raise ValueError(str(e))

    async def delete(self, db: AsyncSession, target_id: int, user_id: int):
        try:
            result = await db.execute(
                select(Target).where(
                    Target.id == target_id,
                    Target.user_id == user_id,
                    Target.deleted_at.is_(None),
                )
            )
            target = result.scalar_one_or_none()

            if not target:
                raise ValueError("Alvo não encontrado")

            target.deleted_at = datetime.utcnow()
            await db.commit()

        except Exception as e:
            await db.rollback()
            raise ValueError(str(e))

    async def restore(self, db: AsyncSession, target_id: int, user_id: int):
        try:
            result = await db.execute(
                select(Target).where(Target.id == target_id, Target.user_id == user_id)
            )
            target = result.scalar_one_or_none()

            if not target:
                raise ValueError("Alvo não encontrado")

            if target.deleted_at is None:
                raise ValueError("Alvo não está deletado")

            target.deleted_at = None
            await db.commit()
            await db.refresh(target)
            return target.to_dict()

        except Exception as e:
            await db.rollback()
            raise ValueError(str(e))
