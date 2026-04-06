from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id
from app.modules.target.controller.target_controller import TargetController
from app.modules.target.schemas.target_schema import TargetCreate, TargetUpdate

router = APIRouter(
    prefix="/targets",
    tags=["Target"]
)

controller = TargetController()


@router.get("/")
async def list_targets(
    owner_type: str = Query("user", pattern="^(user|organization)$"),
    owner_id: int | None = Query(None),
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    resolved_owner_id = owner_id if owner_id is not None else user_id
    return await controller.list_targets(db, user_id, owner_type, resolved_owner_id)


@router.get("/{target_id}")
async def get_target(
    target_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.get_target(db, target_id, user_id)


@router.post("/", status_code=201)
async def create_target(
    payload: TargetCreate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        if payload.organization_id:
            owner_type = "organization"
            owner_id = payload.organization_id
        else:
            owner_type = "user"
            owner_id = user_id

        return await controller.create_target(
            db=db,
            data={
                "name": payload.name,
                "user_id": user_id,
                "owner_type": owner_type,
                "owner_id": owner_id,
                "description": payload.description,
            },
            screen_ids=payload.screen_ids,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{target_id}")
async def update_target(
    target_id: int,
    data: TargetUpdate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        return await controller.update_target(db, target_id, data.dict(exclude_none=True), user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{target_id}", status_code=204)
async def delete_target(
    target_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        await controller.delete_target(db, target_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
