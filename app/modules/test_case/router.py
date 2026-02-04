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

@router.delete("/{test_case_id}")
async def soft_delete(analyses_id: int, test_case_id: int):
    return await controller.soft_delete(analyses_id=analyses_id, test_case_id=test_case_id)


@router.post("/{test_case_id}/restore")
async def restore(analyses_id: int, test_case_id: int, payload: dict = Body(default={})):
    restore_status = payload.get("restore_status", "generated")
    return await controller.restore(
        analyses_id=analyses_id,
        test_case_id=test_case_id,
        restore_status=restore_status,
    )
    
@router.delete("/{test_case_id}/steps/{step_id}")
async def step_soft_delete(analyses_id: int, test_case_id: int, step_id: int):
    return await controller.step_soft_delete(
        analyses_id=analyses_id,
        test_case_id=test_case_id,
        step_id=step_id,
    )


@router.post("/{test_case_id}/steps/{step_id}/restore")
async def step_restore(analyses_id: int, test_case_id: int, step_id: int):
    return await controller.step_restore(
        analyses_id=analyses_id,
        test_case_id=test_case_id,
        step_id=step_id,
    )