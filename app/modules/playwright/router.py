from fastapi import APIRouter, HTTPException

from app.modules.playwright.controller.playwright_controller import PlaywrightController
from app.modules.playwright.schemas.playwright_scripts_schema import (
    PlaywrightScriptCreate,
    PlaywrightScriptUpdate,
    PlaywrightScriptResponse,
)

router = APIRouter(
    prefix="/playwright",
    tags=["Playwright"],
)

controller = PlaywrightController()


@router.get(
    "/target/{target_id}",
    response_model=dict,
)
async def get_scripts_by_target(target_id: int):
    return await controller.index(target_id)


@router.post(
    "/target/{target_id}",
    response_model=dict,
)
async def create_script(
    target_id: int,
    payload: PlaywrightScriptCreate,
):
    if payload.target_id != target_id:
        return {
            "status": False,
            "message": "target_id do path e do body não conferem",
            "data": None,
        }

    return await controller.store(target_id, payload.dict())


@router.put(
    "/target/{target_id}/version/{version}",
    response_model=dict,
)
async def update_script(
    target_id: int,
    version: int,
    payload: PlaywrightScriptUpdate,
):
    return await controller.update(
        target_id=target_id,
        version=version,
        payload=payload.dict(exclude_unset=True),
    )
