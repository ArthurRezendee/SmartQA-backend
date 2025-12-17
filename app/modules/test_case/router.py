
from fastapi import APIRouter
from app.modules.test_case.controller.test_case_controller import TestCaseController

router = APIRouter(
    prefix="/test_case",
    tags=["TestCase"]
)

controller = TestCaseController()


@router.get("/")
async def index():
    return await controller.index()
