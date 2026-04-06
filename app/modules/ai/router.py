import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.ai.controller.ai_controller import AiController
from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id
from app.modules.ai.schemas.analyze_request import AnalyzeRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai",
    tags=["Ai"]
)

controller = AiController()


@router.post("/target/{target_id}")
async def analyze_target(
    target_id: int,
    body: AnalyzeRequest,
    user_id: int = Depends(get_current_user_id),
):
    try:
        result = await controller.analyze_target(
            target_id=target_id,
            user_id=user_id,
            requirements=body.requirements,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao analisar o alvo")


@router.get("/testCase/{target_id}")
async def generate_test_cases(
    target_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return await controller.generate_test_cases(db=db, target_id=target_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao gerar casos de teste")


@router.get("/scriptsPlaywright/{target_id}")
async def generate_scripts_playwright(
    target_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return await controller.generate_scripts_playwright(db=db, target_id=target_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao gerar scripts playwright")


@router.get("/target/{target_id}/jobs")
async def get_target_jobs(
    target_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return await controller.get_target_jobs(
            db=db,
            target_id=target_id,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao buscar jobs do alvo")


@router.post("/documentation/screen/{screen_id}")
async def generate_documentation_for_screen(
    screen_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return await controller.generate_documentation_for_screen(db=db, screen_id=screen_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao gerar documentação")
