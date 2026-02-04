import logging
from fastapi import APIRouter, Depends, HTTPException
from app.modules.ai.controller.ai_controller import AiController
from app.core.database.async_db import get_db
from app.core.dependencies import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai",
    tags=["Ai"]
)

controller = AiController()


@router.get("/testCase/{analysis_id}")
async def generate_test_cases(
    analysis_id: int,
    user_id: int = Depends(get_current_user_id)
):
    try:
        result = await controller.generate_test_cases(
            analysis_id=analysis_id,
            user_id=user_id
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao gerar casos de teste"
        )
        
        
@router.get("/scriptsPlaywright/{analysis_id}")
async def generate_scripts_playwright(
    analysis_id: int,
    user_id: int = Depends(get_current_user_id)
):
    try:
        result = await controller.generate_scripts_playwright(
            analysis_id=analysis_id,
            user_id=user_id
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao gerar scripts playwright" + e
        )
