
from fastapi import APIRouter
from app.modules.organization.controller.organization_controller import OrganizationController

router = APIRouter(
    prefix="/organization",
    tags=["Organization"]
)

controller = OrganizationController()


@router.get("/")
async def index():
    return await controller.index()
