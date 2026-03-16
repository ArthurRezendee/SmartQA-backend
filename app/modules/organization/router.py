from fastapi import APIRouter, Depends
from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id
from app.modules.organization.controller.organization_controller import OrganizationController
from app.modules.organization.schemas.organization_schema import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationMemberAdd,
    OrganizationMemberUpdate,
)

router = APIRouter(
    prefix="/organization",
    tags=["Organization"]
)

controller = OrganizationController()


@router.get("/")
async def list_my_organizations(
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    return await controller.list_my_organizations(db, user_id)


@router.get("/{slug}")
async def get_organization(
    slug: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    return await controller.get_organization(db, slug, user_id)


@router.post("/", status_code=201)
async def create_organization(
    data: OrganizationCreate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    return await controller.create_organization(db, data, user_id)


@router.put("/{slug}")
async def update_organization(
    slug: str,
    data: OrganizationUpdate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    return await controller.update_organization(db, slug, data, user_id)


@router.delete("/{slug}", status_code=204)
async def delete_organization(
    slug: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    await controller.delete_organization(db, slug, user_id)


# ─── Membros ──────────────────────────────────────────────────────────────────

@router.post("/{slug}/members", status_code=201)
async def add_member(
    slug: str,
    data: OrganizationMemberAdd,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    return await controller.add_member(db, slug, data, user_id)


@router.delete("/{slug}/members/{target_user_id}", status_code=204)
async def remove_member(
    slug: str,
    target_user_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    await controller.remove_member(db, slug, target_user_id, user_id)


@router.patch("/{slug}/members/{target_user_id}")
async def update_member_role(
    slug: str,
    target_user_id: int,
    data: OrganizationMemberUpdate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    return await controller.update_member_role(db, slug, target_user_id, data, user_id)