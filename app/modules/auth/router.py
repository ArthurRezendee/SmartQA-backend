from fastapi import APIRouter, Depends
from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id
from app.modules.auth.controller.auth_controller import AuthController
from app.modules.auth.schemas.auth_schema import (
    RegisterSchema,
    LoginSchema,
    GoogleAuthSchema,
    VerifyEmailSchema,
)

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

controller = AuthController()


@router.post("/register")
async def register(data: RegisterSchema, db=Depends(get_db)):
    return await controller.register(db, data)


@router.post("/login")
async def login(data: LoginSchema, db=Depends(get_db)):
    return await controller.login(db, data)


@router.post("/google")
async def google(data: GoogleAuthSchema, db=Depends(get_db)):
    return await controller.google(db, data)


@router.post("/verify-email")
async def verify_email(
    data: VerifyEmailSchema,
    db=Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return await controller.verify_email(db, user_id, data)
