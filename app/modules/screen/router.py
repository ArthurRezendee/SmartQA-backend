from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from typing import List

from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id
from app.modules.screen.controller.screen_controller import ScreenController
from app.modules.screen.schemas.screen_schema import ScreenUpdate

router = APIRouter(
    prefix="/screens",
    tags=["Screen"]
)

controller = ScreenController()


@router.get("/")
async def list_screens(
    owner_type: str = Query("user", pattern="^(user|organization)$"),
    owner_id: int | None = Query(None),
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    resolved_owner_id = owner_id if owner_id is not None else user_id
    return await controller.list_screens(db, user_id, owner_type, resolved_owner_id)


@router.get("/{screen_id}")
async def get_screen(
    screen_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    return await controller.get_screen(db, screen_id, user_id)


@router.post("/", status_code=201)
async def create_screen(
    name: str = Form(...),
    url: str | None = Form(None),
    description: str | None = Form(None),
    screen_context: str | None = Form(None),
    organization_id: int | None = Form(None),
    access_credentials: str | None = Form(None),
    documents: List[UploadFile] = File(default=[]),
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        credentials_list = None
        if access_credentials:
            import json
            credentials_list = json.loads(access_credentials)
            if not isinstance(credentials_list, list):
                raise ValueError("access_credentials deve ser uma lista")

        if organization_id:
            owner_type = "organization"
            owner_id = organization_id
        else:
            owner_type = "user"
            owner_id = user_id

        return await controller.create_screen(
            db=db,
            data={
                "name": name,
                "user_id": user_id,
                "owner_type": owner_type,
                "owner_id": owner_id,
                "url": url,
                "description": description,
                "screen_context": screen_context,
            },
            documents=documents,
            access_credentials=credentials_list,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{screen_id}")
async def update_screen(
    screen_id: int,
    data: ScreenUpdate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        return await controller.update_screen(db, screen_id, data.dict(exclude_none=True), user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{screen_id}", status_code=204)
async def delete_screen(
    screen_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        await controller.delete_screen(db, screen_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
