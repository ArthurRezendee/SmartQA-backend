from fastapi import APIRouter, Depends
from app.core.database.async_db import get_db
from app.modules.plans.controller.plans_controller import PlansController

router = APIRouter(
    prefix="/plans",
    tags=["Plans"]
)

controller = PlansController()


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