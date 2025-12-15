from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import List
import json

from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id
from app.modules.qa_analysis.controller.qa_analysis_controller import QaAnalysisController
from app.modules.qa_analysis.schemas.qa_analysis_schema import QaAnalysisUpdate

router = APIRouter(
    prefix="/qa_analysis",
    tags=["QaAnalysis"]
)

controller = QaAnalysisController()


@router.get("/")
async def list_qa_analysis(
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    return await controller.list_qa_analysis(db, user_id)


@router.get("/{entity_id}")
async def get_qa_analysis(
    entity_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    return await controller.get_qa_analysis(db, entity_id, user_id)


@router.post("/", status_code=201)
async def create_qa_analysis(
    name: str = Form(...),
    target_url: str = Form(...),
    description: str | None = Form(None),
    access_credentials: str | None = Form(None),
    documents: List[UploadFile] = File(default=[]),
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    try:
        credentials_list = None

        if access_credentials:
            credentials_list = json.loads(access_credentials)

            if not isinstance(credentials_list, list):
                raise ValueError("access_credentials deve ser uma lista")

        return await controller.create_qa_analysis(
            db=db,
            data={
                "name": name,
                "user_id": user_id,
                "target_url": target_url,
                "description": description
            },
            documents=documents,
            access_credentials=credentials_list
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{entity_id}")
async def update_qa_analysis(
    entity_id: int,
    data: QaAnalysisUpdate,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    return await controller.update_qa_analysis(db, entity_id, data, user_id)


@router.delete("/{entity_id}", status_code=204)
async def delete_qa_analysis(
    entity_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db)
):
    await controller.delete_qa_analysis(db, entity_id, user_id)
