import logging
import asyncio

from browser_use import Agent, Browser, ChatBrowserUse

from app.core.celery_app import celery_app
from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService
from app.modules.ai.utils.ai_utils import AiUtils
from app.core.database.sync_db import SessionLocal


logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.generate_screen_description",
    autoretry_for=(), 
)
def generate_screen_description(*, analysis_id: int, user_id: int):
    logger.info(
        "🚀 Job GenerateScreenDescription iniciado",
        extra={"analysis_id": analysis_id, "user_id": user_id},
    )

    db = SessionLocal()

    try:
        qa_service = QaAnalysisService()

        analysis = qa_service.get_or_fail_sync(
            db=db,
            entity_id=analysis_id,
            user_id=user_id,
        )

        access_credentials = analysis.get("access_credentials") or []

        if access_credentials:
            credentials_block = "Realize o login seguindo exatamente os passos abaixo:\n"
            for cred in access_credentials:
                credentials_block += (
                    f'- Preencha o campo "{cred["field_name"]}" '
                    f'com o valor "{cred["value"]}".\n'
                )
        else:
            credentials_block = (
                "Caso a tela não exija autenticação, apenas acesse a página normalmente.\n"
            )

        task = f"""
Acesse a URL abaixo:
{analysis["target_url"]}

{credentials_block}

Após o carregamento completo da página:
- explore a tela: abas, modais, etc. Desde que não saia da tela para outra URL.

Descreva detalhadamente a interface explorada da tela. Essa descrição é para um agente responsável pela geração de casos de teste dessa tela.
Então se atente nos detalhes na sua exploração.
Retorne SOMENTE a descrição da interface, sem textos adicionais.
""".strip()

        browser = Browser(
            headless=True,
            executable_path="/root/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome",
        )

        llm = ChatBrowserUse()

        agent = Agent(
            task=task,
            browser=browser,
            llm=llm,
        )

        history = asyncio.run(agent.run())

        ui_description = history.final_result()

        if not ui_description:
            raise ValueError("Não foi possível obter descrição da interface")

        ui_description = ui_description.strip()

        prompt = AiUtils.build_test_case_prompt(
            ui_description=ui_description,
            analysis=analysis,
        )

        logger.info(f"🖥️ UI DESCRIPTION:\n{ui_description}")
        logger.info(f"🧪 TEST CASE PROMPT:\n{prompt}")

        logger.info("✅ Job GenerateScreenDescription finalizado com sucesso")

        return {
            "analysis_id": analysis_id,
            "status": "completed",
        }

    except Exception:
        logger.exception("❌ Erro no job GenerateScreenDescription")
        raise

    finally:
        db.close()
