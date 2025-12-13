
from fastapi import APIRouter, Depends
from app.modules.qa_analysis.controller.qa_analysis_controller import QaAnalysisController
from app.modules.qa_analysis.schemas.qa_analysis_schema import QaAnalysisCreate, QaAnalysisUpdate
from app.core.database import get_db


router = APIRouter(
    prefix="/qa_analysis",
    tags=["QaAnalysis"]
)

controller = QaAnalysisController()


# QaAnalysis CRUD
@router.get("/")
async def list_qa_analysis(db=Depends(get_db)):
    return await controller.list_qa_analysis(db)

@router.get("/{entity_id}")
async def get_qa_analysis(entity_id: int, db=Depends(get_db)):
    return await controller.get_qa_analysis(db, entity_id)

@router.post("/")
async def create_qa_analysis(data: QaAnalysisCreate, db=Depends(get_db)):
    return await controller.create_qa_analysis(db, data)

@router.put("/{entity_id}")
async def update_qa_analysis(entity_id: int, data: QaAnalysisUpdate, db=Depends(get_db)):
    return await controller.update_qa_analysis(db, entity_id, data)

@router.delete("/{entity_id}")
async def delete_qa_analysis(entity_id: int, db=Depends(get_db)):
    return await controller.delete_qa_analysis(db, entity_id)
