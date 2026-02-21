
from fastapi import APIRouter
from app.modules.plans.controller.plans_controller import PlansController

router = APIRouter(
    prefix="/plans",
    tags=["Plans"]
)

controller = PlansController()


@router.get("/")
async def index():
    return await controller.index()
