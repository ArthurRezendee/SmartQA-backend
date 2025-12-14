import os
from browser_use_sdk import BrowserUse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService
from app.modules.ai.utils.ai_utils import AiUtils


class AiService:

    def __init__(self):
        self.client = BrowserUse(api_key=os.getenv("BROWSER_USE_API_KEY"))

    async def generate_test_cases(
        self,
        db: AsyncSession,
        analysis_id: int,
        user_id: int
    ):
        try:
            qa_service = QaAnalysisService()

            analysis = await qa_service.get_or_fail(db, analysis_id, user_id)

            browser = BrowserUse(api_key=os.getenv("BROWSER_USE_API_KEY"))

            task = browser.tasks.create_task(
                task=f"""
                Acesse a URL {analysis["target_url"]}.
                Caso exista autenticação, utilize as credenciais fornecidas.
                Descreva detalhadamente a interface visível após o carregamento.
                Me retorne somente a descrição, de forma direta e detalhada, sem mais nenhum texto.
                """,
                llm="browser-use-llm"
            )

            result = task.complete()

            if not result or not result.output:
                raise ValueError("Não foi possível obter descrição da interface")

            ui_description = result.output

            prompt = AiUtils.build_test_case_prompt(ui_description)

            return {
                "analysis_id": analysis_id,
                "ui_description": ui_description,
                "prompt": prompt
            }

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Erro ao gerar casos de teste: {str(e)}")
