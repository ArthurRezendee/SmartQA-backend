from fastapi import APIRouter, Body
from app.modules.test_case.controller.test_case_controller import TestCaseController

router = APIRouter(
    prefix="/test_cases/{target_id}",
    tags=["TestCase"]
)

controller = TestCaseController()


@router.get("/")
async def index(target_id: int):
    return await controller.index(target_id=target_id)


@router.post("/")
async def store(target_id: int, payload: dict = Body(...)):
    return await controller.store(target_id=target_id, payload=payload)


@router.put("/{test_case_id}")
async def update(target_id: int, test_case_id: int, payload: dict = Body(...)):
    return await controller.update(
        target_id=target_id,
        test_case_id=test_case_id,
        payload=payload,
    )


@router.delete("/{test_case_id}")
async def soft_delete(target_id: int, test_case_id: int):
    return await controller.soft_delete(target_id=target_id, test_case_id=test_case_id)


@router.post("/{test_case_id}/restore")
async def restore(target_id: int, test_case_id: int, payload: dict = Body(default={})):
    restore_status = payload.get("restore_status", "generated")
    return await controller.restore(
        target_id=target_id,
        test_case_id=test_case_id,
        restore_status=restore_status,
    )


@router.delete("/{test_case_id}/steps/{step_id}")
async def step_soft_delete(target_id: int, test_case_id: int, step_id: int):
    return await controller.step_soft_delete(
        target_id=target_id,
        test_case_id=test_case_id,
        step_id=step_id,
    )


@router.post("/{test_case_id}/steps/{step_id}/restore")
async def step_restore(target_id: int, test_case_id: int, step_id: int):
    return await controller.step_restore(
        target_id=target_id,
        test_case_id=test_case_id,
        step_id=step_id,
    )


@router.get("/export", status_code=200)
async def export_test_cases(target_id: int):
    return await controller.export_test_cases(target_id=target_id)
