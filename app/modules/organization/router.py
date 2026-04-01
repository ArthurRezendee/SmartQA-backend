from fastapi import APIRouter, Depends

from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id
from app.modules.organization.controller.organization_controller import OrganizationController
from app.modules.organization.controller.invitation_controller import InvitationController
from app.modules.organization.schemas.organization_schema import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationMemberAdd,
    OrganizationMemberUpdate,
    OrganizationInviteCreate,
    InvitationRespond,
)

router = APIRouter(
    prefix="/organization",
    tags=["Organization"],
)

controller = OrganizationController()
invite_controller = InvitationController()


# ─── Organizações ─────────────────────────────────────────────────────────────

@router.get("/")
async def list_my_organizations(
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.list_my_organizations(db, user_id)


@router.post("/", status_code=201)
async def create_organization(
    data: OrganizationCreate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.create_organization(db, data, user_id)


# ─── Convites (rotas estáticas devem vir ANTES de /{slug}) ───────────────────

@router.get("/invitations/{token}")
async def get_invitation_info(
    token: str,
    db=Depends(get_db),
):
    """Endpoint público — retorna dados do convite para exibir na tela de convite."""
    return await invite_controller.get_invitation_info(db, token)


@router.post("/invitations/{token}/respond")
async def respond_to_invitation(
    token: str,
    data: InvitationRespond,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Aceitar ou recusar um convite (requer autenticação)."""
    return await invite_controller.respond_to_invitation(db, token, data.action, user_id)


# ─── Operações por slug ───────────────────────────────────────────────────────

@router.get("/{slug}")
async def get_organization(
    slug: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.get_organization(db, slug, user_id)


@router.put("/{slug}")
async def update_organization(
    slug: str,
    data: OrganizationUpdate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.update_organization(db, slug, data, user_id)


@router.delete("/{slug}", status_code=204)
async def delete_organization(
    slug: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    await controller.delete_organization(db, slug, user_id)


# ─── Membros ──────────────────────────────────────────────────────────────────

@router.post("/{slug}/members", status_code=201)
async def add_member(
    slug: str,
    data: OrganizationMemberAdd,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.add_member(db, slug, data, user_id)


@router.delete("/{slug}/members/{target_user_id}", status_code=204)
async def remove_member(
    slug: str,
    target_user_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    await controller.remove_member(db, slug, target_user_id, user_id)


@router.patch("/{slug}/members/{target_user_id}")
async def update_member_role(
    slug: str,
    target_user_id: int,
    data: OrganizationMemberUpdate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.update_member_role(db, slug, target_user_id, data, user_id)


# ─── Gerenciamento de convites da org (owner/admin) ───────────────────────────

@router.post("/{slug}/invite", status_code=201)
async def invite_member(
    slug: str,
    data: OrganizationInviteCreate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Convidar usuário por e-mail para a organização."""
    return await invite_controller.invite(db, slug, data.email, data.role, user_id)


@router.get("/{slug}/invitations")
async def list_invitations(
    slug: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Listar todos os convites da organização (owner/admin)."""
    return await invite_controller.list_org_invitations(db, slug, user_id)


@router.delete("/{slug}/invitations/{invitation_id}", status_code=204)
async def cancel_invitation(
    slug: str,
    invitation_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    """Cancelar um convite pendente (owner/admin)."""
    await invite_controller.cancel_invitation(db, invitation_id, user_id)
