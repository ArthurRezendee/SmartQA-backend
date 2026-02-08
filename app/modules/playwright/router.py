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
    "/analysis/{analysis_id}",
    response_model=dict,  # segue padrão { status, message, data }
)
async def get_scripts_by_analysis(analysis_id: int):
    return await controller.index(analysis_id)


@router.post(
    "/analysis/{analysis_id}",
    response_model=dict,
)
async def create_script(
    analysis_id: int,
    payload: PlaywrightScriptCreate,
):
    if payload.analysis_id != analysis_id:
        return {
            "status": False,
            "message": "analysis_id do path e do body não conferem",
            "data": None,
        }

    return await controller.store(analysis_id, payload.dict())


@router.put(
    "/analysis/{analysis_id}/version/{version}",
    response_model=dict,
)
async def update_script(
    analysis_id: int,
    version: int,
    payload: PlaywrightScriptUpdate,
):
    return await controller.update(
        analysis_id=analysis_id,
        version=version,
        payload=payload.dict(exclude_unset=True),
    )
