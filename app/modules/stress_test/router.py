from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import io

from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id
from app.modules.stress_test.controller.stress_test_controller import StressTestController

router = APIRouter(prefix="/stress-tests", tags=["Stress Test"])

controller = StressTestController()


@router.post("/target/{target_id}", status_code=201)
async def create_stress_test(
    target_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        stress_test = await controller.create(db, target_id, user_id)

        from app.core.celery_app import celery_app
        celery_app.send_task(
            "jobs.ia.run_stress_test",
            kwargs={
                "stress_test_id": stress_test["id"],
                "target_id": target_id,
                "user_id": user_id,
            },
        )

        return stress_test
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/target/{target_id}")
async def list_stress_tests(
    target_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        return await controller.list_by_target(db, target_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{stress_test_id}")
async def get_stress_test(
    stress_test_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        return await controller.get(db, stress_test_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{stress_test_id}/steps")
async def get_stress_test_steps(
    stress_test_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        return await controller.get_steps(db, stress_test_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{stress_test_id}/export")
async def export_stress_test_report(
    stress_test_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        pdf_bytes = await controller.export_report(db, stress_test_id, user_id)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=stress_test_{stress_test_id}_report.pdf"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{stress_test_id}", status_code=204)
async def delete_stress_test(
    stress_test_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    try:
        await controller.delete(db, stress_test_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
