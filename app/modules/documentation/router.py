from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.core.database.sync_db import SessionLocal
from app.modules.documentation.controller.documentations_controller import (
    DocumentationsController,
)

router = APIRouter(
    prefix="/documentations",
    tags=["Documentations"],
)

controller = DocumentationsController()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================
# GETs por tela (Screen)
# ============================

@router.get("/screen/{screen_id}")
def list_by_screen(
    screen_id: int,
    db: Session = Depends(get_db),
):
    return controller.get_by_screen(db, screen_id)


@router.get("/screen/{screen_id}/latest")
def get_latest(
    screen_id: int,
    db: Session = Depends(get_db),
):
    doc = controller.get_latest_by_screen(db, screen_id)

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma documentação encontrada para esta tela",
        )

    return doc


# ============================
# PUT – update manual
# ============================

@router.put("/{documentation_id}")
def update_documentation(
    documentation_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    result = controller.update(db, documentation_id, payload)

    if not result["status"]:
        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )

    return result


# ============================
# Export
# ============================

@router.get("/export/{documentation_id}")
def export_documentation(
    documentation_id: int,
    db: Session = Depends(get_db),
):
    return controller.export(db, documentation_id)
