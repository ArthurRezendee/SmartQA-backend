
from fastapi import APIRouter
from app.modules.ia.controller.ia_controller import IaController

router = APIRouter(
    prefix="/ia",
    tags=["Ia"]
)

controller = IaController()


@router.get("/")
async def index():
    return await controller.index()
