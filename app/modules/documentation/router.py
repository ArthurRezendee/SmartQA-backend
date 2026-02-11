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
# GETs
# ============================

@router.get("/analysis/{analysis_id}")
def list_by_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    """
    Lista todas as documentações de uma análise
    """
    return controller.get_by_analysis(db, analysis_id)


@router.get("/analysis/{analysis_id}/latest")
def get_latest(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    """
    Retorna a documentação mais recente da análise
    """
    doc = controller.get_latest_by_analysis(db, analysis_id)

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma documentação encontrada para esta análise",
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
    """
    Atualiza uma documentação existente (edição manual)
    """
    result = controller.update(db, documentation_id, payload)

    if not result["status"]:
        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )

    return result
