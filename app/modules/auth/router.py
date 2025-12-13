from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.modules.auth.controller.auth_controller import AuthController
from app.modules.auth.schemas.auth_schema import (
    RegisterSchema,
    LoginSchema,
    GoogleAuthSchema
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
