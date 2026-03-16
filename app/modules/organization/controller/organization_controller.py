from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.shared.controller import BaseController
from app.shared.responses import success, error
from app.modules.organization.model.organization_model import Organization, OrganizationMember
from app.modules.organization.schemas.organization_schema import OrganizationCreate, OrganizationUpdate, OrganizationMemberAdd, OrganizationMemberUpdate
from app.modules.billing.model.billing_account_model import BillingAccount


class OrganizationController(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return success("Organization module ready", None)

    # ─── Listar orgs do usuário ───────────────────────────────────────────────

    async def list_my_organizations(self, db: AsyncSession, user_id: int):
        try:
            result = await db.execute(
                select(Organization)
                .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
                .where(
                    and_(
                        OrganizationMember.user_id == user_id,
                        Organization.is_active == True
                    )
                )
                .options(
                    selectinload(Organization.members),
                    selectinload(Organization.billing_account).selectinload(BillingAccount.plan)
                )
            )
            orgs = result.scalars().all()

            data = []
            for org in orgs:
                member = next((m for m in org.members if m.user_id == user_id), None)
                billing = org.billing_account

                data.append({
                    "id": org.id,
                    "name": org.name,
                    "slug": org.slug,
                    "description": org.description,
                    "avatar_color": org.avatar_color,
                    "owner_id": org.owner_id,
                    "role": member.role if member else "member",
                    "member_count": len(org.members),
                    "plan": billing.plan.name if billing and billing.plan else None,
                    "plan_slug": billing.plan.slug if billing and billing.plan else None,
                    "is_active": org.is_active,
                    "created_at": org.created_at.isoformat() if org.created_at else None,
                })

            return success("Organizações recuperadas", data)

        except Exception as e:
            return error(f"Erro ao buscar organizações: {str(e)}")

    # ─── Buscar org por slug ──────────────────────────────────────────────────

    async def get_organization(self, db: AsyncSession, slug: str, user_id: int):
        try:
            result = await db.execute(
                select(Organization)
                .where(
                    and_(
                        Organization.slug == slug,
                        Organization.is_active == True
                    )
                )
                .options(
                    selectinload(Organization.members),
                    selectinload(Organization.billing_account).selectinload(BillingAccount.plan)
                )
            )
            org = result.scalar_one_or_none()

            if not org:
                return error("Organização não encontrada", status_code=404)

            # verifica se usuário é membro
            member = next((m for m in org.members if m.user_id == user_id), None)
            if not member:
                return error("Acesso negado", status_code=403)

            billing = org.billing_account

            return success("Organização recuperada", {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "description": org.description,
                "avatar_color": org.avatar_color,
                "owner_id": org.owner_id,
                "role": member.role,
                "member_count": len(org.members),
                "members": [
                    {
                        "user_id": m.user_id,
                        "role": m.role,
                        "accepted_at": m.accepted_at.isoformat() if m.accepted_at else None,
                    }
                    for m in org.members
                ],
                "plan": billing.plan.name if billing and billing.plan else None,
                "plan_slug": billing.plan.slug if billing and billing.plan else None,
                "billing_status": billing.subscription_status if billing else None,
                "is_active": org.is_active,
                "created_at": org.created_at.isoformat() if org.created_at else None,
            })

        except Exception as e:
            return error(f"Erro ao buscar organização: {str(e)}")

    # ─── Criar org ────────────────────────────────────────────────────────────

    async def create_organization(self, db: AsyncSession, data: OrganizationCreate, user_id: int):
        try:
            # verifica slug único
            existing = await db.execute(
                select(Organization).where(Organization.slug == data.slug)
            )
            if existing.scalar_one_or_none():
                return error("Slug já está em uso")

            # cria org
            org = Organization(
                name=data.name,
                slug=data.slug,
                description=data.description,
                avatar_color=data.avatar_color,
                owner_id=user_id,
            )
            db.add(org)
            await db.flush()  # pega o org.id antes do commit

            # cria billing account vinculado à org
            billing = BillingAccount(
                type="organization",
                plan_id=data.plan_id,
                organization_id=org.id,
                subscription_status="active",
                analyses_used_current_cycle=0,
            )
            db.add(billing)
            await db.flush()

            # adiciona criador como owner
            member = OrganizationMember(
                organization_id=org.id,
                user_id=user_id,
                role="owner",
            )
            db.add(member)

            await db.commit()
            await db.refresh(org)

            return success("Organização criada com sucesso", {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "description": org.description,
                "avatar_color": org.avatar_color,
                "owner_id": org.owner_id,
                "role": "owner",
                "member_count": 1,
                "plan_id": data.plan_id,
                "created_at": org.created_at.isoformat() if org.created_at else None,
            }, status_code=201)

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao criar organização: {str(e)}")

    # ─── Atualizar org ────────────────────────────────────────────────────────

    async def update_organization(self, db: AsyncSession, slug: str, data: OrganizationUpdate, user_id: int):
        try:
            result = await db.execute(
                select(Organization).where(Organization.slug == slug)
            )
            org = result.scalar_one_or_none()

            if not org:
                return error("Organização não encontrada", status_code=404)

            if org.owner_id != user_id:
                return error("Apenas o owner pode editar a organização", status_code=403)

            for field, value in data.dict(exclude_unset=True).items():
                setattr(org, field, value)

            await db.commit()
            await db.refresh(org)

            return success("Organização atualizada", {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "description": org.description,
                "avatar_color": org.avatar_color,
            })

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao atualizar organização: {str(e)}")

    # ─── Deletar org ──────────────────────────────────────────────────────────

    async def delete_organization(self, db: AsyncSession, slug: str, user_id: int):
        try:
            result = await db.execute(
                select(Organization).where(Organization.slug == slug)
            )
            org = result.scalar_one_or_none()

            if not org:
                return error("Organização não encontrada", status_code=404)

            if org.owner_id != user_id:
                return error("Apenas o owner pode deletar a organização", status_code=403)

            org.is_active = False
            await db.commit()

            return success("Organização desativada com sucesso", None)

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao deletar organização: {str(e)}")

    # ─── Membros ──────────────────────────────────────────────────────────────

    async def add_member(self, db: AsyncSession, slug: str, data: OrganizationMemberAdd, user_id: int):
        try:
            result = await db.execute(
                select(Organization)
                .where(Organization.slug == slug)
                .options(
                    selectinload(Organization.members),
                    selectinload(Organization.billing_account).selectinload(BillingAccount.plan)
                )
            )
            org = result.scalar_one_or_none()

            if not org:
                return error("Organização não encontrada", status_code=404)

            # só owner/admin pode adicionar
            requester = next((m for m in org.members if m.user_id == user_id), None)
            if not requester or requester.role not in ("owner", "admin"):
                return error("Sem permissão para adicionar membros", status_code=403)

            # verifica limite do plano
            billing = org.billing_account
            if billing and billing.plan:
                if len(org.members) >= billing.plan.max_users:
                    return error(f"Limite de {billing.plan.max_users} membros atingido no plano {billing.plan.name}")

            # verifica se já é membro
            already = next((m for m in org.members if m.user_id == data.user_id), None)
            if already:
                return error("Usuário já é membro desta organização")

            member = OrganizationMember(
                organization_id=org.id,
                user_id=data.user_id,
                role=data.role,
                invited_by_id=user_id,
            )
            db.add(member)
            await db.commit()

            return success("Membro adicionado com sucesso", {
                "user_id": data.user_id,
                "role": data.role,
            }, status_code=201)

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao adicionar membro: {str(e)}")

    async def remove_member(self, db: AsyncSession, slug: str, target_user_id: int, user_id: int):
        try:
            result = await db.execute(
                select(Organization)
                .where(Organization.slug == slug)
                .options(selectinload(Organization.members))
            )
            org = result.scalar_one_or_none()

            if not org:
                return error("Organização não encontrada", status_code=404)

            requester = next((m for m in org.members if m.user_id == user_id), None)
            if not requester or requester.role not in ("owner", "admin"):
                return error("Sem permissão para remover membros", status_code=403)

            if org.owner_id == target_user_id:
                return error("Não é possível remover o owner da organização")

            target = next((m for m in org.members if m.user_id == target_user_id), None)
            if not target:
                return error("Membro não encontrado", status_code=404)

            await db.delete(target)
            await db.commit()

            return success("Membro removido com sucesso", None)

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao remover membro: {str(e)}")

    async def update_member_role(self, db: AsyncSession, slug: str, target_user_id: int, data: OrganizationMemberUpdate, user_id: int):
        try:
            result = await db.execute(
                select(Organization)
                .where(Organization.slug == slug)
                .options(selectinload(Organization.members))
            )
            org = result.scalar_one_or_none()

            if not org:
                return error("Organização não encontrada", status_code=404)

            requester = next((m for m in org.members if m.user_id == user_id), None)
            if not requester or requester.role != "owner":
                return error("Apenas o owner pode alterar roles", status_code=403)

            target = next((m for m in org.members if m.user_id == target_user_id), None)
            if not target:
                return error("Membro não encontrado", status_code=404)

            target.role = data.role
            await db.commit()

            return success("Role atualizado com sucesso", {
                "user_id": target_user_id,
                "role": data.role,
            })

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao atualizar role: {str(e)}")