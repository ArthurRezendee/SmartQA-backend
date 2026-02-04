
from fastapi import APIRouter
from app.modules.playwright.controller.playwright_controller import PlaywrightController

router = APIRouter(
    prefix="/playwright",
    tags=["Playwright"]
)

controller = PlaywrightController()


@router.get("/")
async def index():
    return await controller.index()
