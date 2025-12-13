
from fastapi import APIRouter, Depends
from app.modules.user.controller.user_controller import UserController
from app.core.database import get_db
from app.modules.user.schemas.user_schema import UserCreate, UserUpdate

router = APIRouter(
    prefix="/user",
    tags=["User"]
)

controller = UserController()


@router.get("/")
async def index():
    return await controller.index()


# User CRUD
@router.get("/users")
async def list_users(db=Depends(get_db)):
    return await controller.list_users(db)

@router.get("/users/{entity_id}")
async def get_user(entity_id: int, db=Depends(get_db)):
    return await controller.get_user(db, entity_id)

@router.post("/users")
async def create_user(data: UserCreate, db=Depends(get_db)):
    return await controller.create_user(db, data)

@router.put("/users/{entity_id}")
async def update_user(entity_id: int, data: UserUpdate, db=Depends(get_db)):
    return await controller.update_user(db, entity_id, data)

@router.delete("/users/{entity_id}")
async def delete_user(entity_id: int, db=Depends(get_db)):
    return await controller.delete_user(db, entity_id)
