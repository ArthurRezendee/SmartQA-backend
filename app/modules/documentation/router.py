
from fastapi import APIRouter
from app.modules.documentation.controller.documentations_controller import DocumentationsController

router = APIRouter(
    prefix="/documentations",
    tags=["Documentations"]
)

controller = DocumentationsController()


@router.get("/")
async def index():
    return await controller.index()
