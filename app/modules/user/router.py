
from fastapi import APIRouter
from app.modules.user.controller.user_controller import UserController

router = APIRouter(
    prefix="/user",
    tags=["User"]
)

controller = UserController()


@router.get("/")
async def index():
    return await controller.index()
