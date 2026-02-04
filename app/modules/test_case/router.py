from fastapi import APIRouter, Body
from app.modules.test_case.controller.test_case_controller import TestCaseController

router = APIRouter(
    prefix="/test_cases/{analyses_id}",
    tags=["TestCase"]
)

controller = TestCaseController()


@router.get("/")
async def index(analyses_id: int):
    return await controller.index(analyses_id=analyses_id)


@router.post("/")
async def store(analyses_id: int, payload: dict = Body(...)):
    return await controller.store(analyses_id=analyses_id, payload=payload)


@router.put("/{test_case_id}")
async def update(analyses_id: int, test_case_id: int, payload: dict = Body(...)):
    return await controller.update(
        analyses_id=analyses_id,
        test_case_id=test_case_id,
        payload=payload,
    )
