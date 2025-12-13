from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import List
from app.core.database import get_db
from app.modules.qa_analysis.controller.qa_analysis_controller import QaAnalysisController
from app.modules.qa_analysis.schemas.qa_analysis_schema import QaAnalysisCreate, QaAnalysisUpdate

router = APIRouter(
    prefix="/qa_analysis",
    tags=["QaAnalysis"]
)

controller = QaAnalysisController()


@router.get("/")
async def list_qa_analysis(db=Depends(get_db)):
    return await controller.list_qa_analysis(db)


@router.get("/{entity_id}")
async def get_qa_analysis(entity_id: int, db=Depends(get_db)):
    return await controller.get_qa_analysis(db, entity_id)


@router.post("/", status_code=201)
async def create_qa_analysis(
    name: str = Form(...),
    user_id: int = Form(...),
    target_url: str = Form(...),
    description: str | None = Form(None),
    documents: List[UploadFile] = File(default=[]),
    db=Depends(get_db)
):
    try:
        return await controller.create_qa_analysis(
            db=db,
            data={
                "name": name,
                "user_id": user_id,
                "target_url": target_url,
                "description": description
            },
            documents=documents
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{entity_id}")
async def update_qa_analysis(
    entity_id: int,
    data: QaAnalysisUpdate,
    db=Depends(get_db)
):
    return await controller.update_qa_analysis(db, entity_id, data)


@router.delete("/{entity_id}", status_code=204)
async def delete_qa_analysis(entity_id: int, db=Depends(get_db)):
    await controller.delete_qa_analysis(db, entity_id)
