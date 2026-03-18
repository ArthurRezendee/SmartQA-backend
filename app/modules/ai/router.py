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

@router.post("/analysis/{analysis_id}")
async def analyze_target(
    analysis_id: int,
    body: AnalyzeRequest,
    user_id: int = Depends(get_current_user_id)
):
    try:
        result = await controller.analyze_target(
            analysis_id=analysis_id,
            user_id=user_id,
            requirements=body.requirements
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao analisar o alvo"
        )
        
# casos de teste
@router.get("/testCase/{analysis_id}")
async def generate_test_cases(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return await controller.generate_test_cases(db=db, analysis_id=analysis_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao gerar casos de teste")

# testes automatizados
@router.get("/scriptsPlaywright/{analysis_id}")
async def generate_scripts_playwright(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return await controller.generate_scripts_playwright(db=db, analysis_id=analysis_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao gerar scripts playwright")

@router.get("/analysis/{analysis_id}/jobs")
async def get_analysis_jobs(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return await controller.get_analysis_jobs(
            db=db,
            analysis_id=analysis_id,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao buscar jobs da análise")


# documentacao
@router.get("/documentation/{analysis_id}")
async def generate_documentation(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    try:
        return await controller.generate_documentation(db=db, analysis_id=analysis_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao gerar documentação")
