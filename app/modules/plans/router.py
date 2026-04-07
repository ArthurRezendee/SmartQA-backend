from fastapi import APIRouter, Depends
from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id
from app.modules.plans.controller.plans_controller import PlansController

router = APIRouter(
    prefix="/plans",
    tags=["Plans"]
)

controller = PlansController()


@router.get("/me")
async def get_my_plan(
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    return await controller.get_my_plan(db, user_id)


@router.get("/")
async def list_plans(
    scope: str | None = None,
    db=Depends(get_db)
):
    return await controller.list_plans(db, scope)


@router.get("/{plan_id}")
async def get_plan(
    plan_id: int,
    db=Depends(get_db)
):
    return await controller.get_plan(db, plan_id)