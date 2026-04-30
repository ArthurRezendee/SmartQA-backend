import asyncio
import logging
import os

from browser_use import Agent, Browser
from browser_use.llm import ChatOpenAI

from app.modules.ai.utils.ai_utils import AiUtils

logger = logging.getLogger(__name__)

_BROWSER_EXECUTABLE = os.getenv("BROWSER_EXECUTABLE_PATH", "/root/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome")
_STRESS_TEST_MODEL = os.getenv("STRESS_TEST_MODEL", "gpt-4.1")

_CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-setuid-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
]

_RECON_MAX_STEPS = 80
_MAX_ATTEMPTS = 2


class PageNotLoadedError(Exception):
    """A página alvo não carregou após todas as tentativas do agente."""


class NoElementsFoundError(Exception):
    """A página carregou mas nenhum elemento interativo foi encontrado."""


class StressTestReconService:

    def run_recon(self, *, analysis: dict) -> dict:
        """
        Roda o agente de reconhecimento e retorna o element_map estruturado:
        {"fields": [...], "buttons": [...]}

        Lança PageNotLoadedError ou NoElementsFoundError em vez de mensagens técnicas.
        """
        credentials_block = AiUtils.build_credentials_block(
            analysis.get("access_credentials") or [],
            target_url=analysis.get("target_url", ""),
        )
        task = AiUtils.build_recon_prompt(
            target_url=analysis.get("target_url", ""),
            credentials_block=credentials_block,
            screen_context=(analysis.get("screen_context") or ""),
        )

        llm = ChatOpenAI(model=_STRESS_TEST_MODEL)

        last_error = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            browser = Browser(
                headless=True,
                executable_path=_BROWSER_EXECUTABLE,
                args=_CHROMIUM_ARGS,
                minimum_wait_page_load_time=2.0,
                wait_for_network_idle_page_load_time=3.0,
            )
            try:
                agent = Agent(
                    task=task,
                    browser=browser,
                    llm=llm,
                    vision_detail_level="low",
                    max_history_items=12,
                    llm_screenshot_size=(1280, 800),
                    use_thinking=False,
                    use_judge=False,
                    max_failures=5,
                )
                history = asyncio.run(agent.run(max_steps=_RECON_MAX_STEPS))
                result = (history.final_result() or "").strip()
            finally:
                try:
                    asyncio.run(browser.close())
                except Exception:
                    pass

            if not result:
                last_error = "resultado vazio do agente"
                logger.warning(f"[Recon] Tentativa {attempt}/{_MAX_ATTEMPTS}: {last_error}")
                continue

            try:
                data = AiUtils.parse_browseruse_json(result)
            except Exception as e:
                last_error = f"resposta não-JSON do agente: {e}"
                logger.warning(f"[Recon] Tentativa {attempt}/{_MAX_ATTEMPTS}: {last_error}")
                continue

            if data.get("page_failed"):
                raise PageNotLoadedError()

            fields  = data.get("fields")  or []
            buttons = data.get("buttons") or []

            if not fields and not buttons:
                last_error = "nenhum elemento encontrado"
                logger.warning(f"[Recon] Tentativa {attempt}/{_MAX_ATTEMPTS}: {last_error}")
                continue

            logger.info(f"[Recon] Mapeamento concluído: {len(fields)} campos, {len(buttons)} botões")
            return {"fields": fields, "buttons": buttons}

        # Determina o tipo correto de erro para o último problema visto
        if last_error == "nenhum elemento encontrado":
            raise NoElementsFoundError()
        raise PageNotLoadedError()
