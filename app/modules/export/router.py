
from fastapi import APIRouter
from app.modules.export.controller.export_controller import ExportController

router = APIRouter(
    prefix="/export",
    tags=["Export"]
)

controller = ExportController()


@router.get("/")
async def index():
    return await controller.index()
