
from fastapi import APIRouter
from app.modules.email.controller.email_controller import EmailController

router = APIRouter(
    prefix="/email",
    tags=["Email"]
)

controller = EmailController()


@router.get("/")
async def index():
    return await controller.index()
