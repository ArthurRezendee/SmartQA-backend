
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from app.modules.email.controller.email_controller import EmailController

router = APIRouter(
    prefix="/email",
    tags=["Email"]
)

controller = EmailController()


class TestEmailSchema(BaseModel):
    to: EmailStr


@router.get("/")
async def index():
    return await controller.index()


@router.post("/test")
async def test(data: TestEmailSchema):
    return await controller.test(data.to)
