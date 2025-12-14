from fastapi import APIRouter, Depends, HTTPException
from app.modules.ai.controller.ai_controller import AiController
from app.core.database import get_db
from app.core.dependencies import get_current_user_id

router = APIRouter(
    prefix="/ai",
    tags=["Ai"]
)

controller = AiController()


@router.get("/testCase/{analysis_id}")
async def generate_test_cases(
    analysis_id: int,
    db=Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    try:
        return await controller.generate_test_cases(db, analysis_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao gerar casos de teste")
