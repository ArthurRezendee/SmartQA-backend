import asyncio
import logging
import time
from browser_use import Agent, Browser, ChatBrowserUse
from app.modules.ai.utils.ai_utils import AiUtils
import os

logger = logging.getLogger(__name__)

_BROWSER_EXECUTABLE = os.getenv("BROWSER_EXECUTABLE_PATH", "/root/.cache/ms-playwright/chromium-1200/chrome-linux-64")
_RETRY_DELAY_SECONDS = 5


class ScreenExplorerService:
    def generate_screen_descriptions(self, *, analysis: dict) -> dict:
        credentials_block = AiUtils.build_credentials_block(
            analysis.get("access_credentials") or []
        )

        llm = ChatBrowserUse()

        required = {
            "tests_description",
            "playwright_description",
            "documentation_description",
            "uiux_description",
        }

        def _validate(data: dict) -> dict:
            if not isinstance(data, dict):
                raise ValueError(f"BrowserUse retornou tipo inválido: {type(data)}")

            missing = required - set(data.keys())
            if missing:
                raise ValueError(f"BrowserUse retornou JSON sem chaves obrigatórias: {missing}")

            data = {k: data.get(k) for k in required}

            for k in required:
                if not isinstance(data.get(k), str) or not data[k].strip():
                    raise ValueError(f"Campo '{k}' vazio ou inválido no retorno do BrowserUse")

            return {
                "tests_description": data["tests_description"].strip(),
                "playwright_description": data["playwright_description"].strip(),
                "documentation_description": data["documentation_description"].strip(),
                "uiux_description": data["uiux_description"].strip(),
            }

        def _run_agent(task: str) -> str:
            # Cria um browser novo a cada tentativa para evitar estado corrompido
            browser = Browser(
                headless=True,
                executable_path=_BROWSER_EXECUTABLE,
            )
            try:
                agent = Agent(
                    task=task,
                    browser=browser,
                    llm=llm,
                )
                history = asyncio.run(agent.run())
                result = (history.final_result() or "").strip()
            finally:
                try:
                    asyncio.run(browser.close())
                except Exception:
                    pass

            if not result:
                raise ValueError("Não foi possível obter retorno do BrowserUse")

            return result

        base_task = AiUtils.build_explorer_prompt(
            analysis=analysis,
            credentials_block=credentials_block,
        )

        compact_task = (
            base_task
            + "\n\n"
            + """
IMPORTANTE (ANTI-TRUNCAMENTO):
- Cada campo deve ter NO MÁXIMO 1200 caracteres
- Seja direto e objetivo
- Não repita informações
- Retorne APENAS JSON válido
""".strip()
        )

        last_error = None

        for attempt, task in enumerate([base_task, compact_task, compact_task], start=1):
            try:
                result = _run_agent(task)

                try:
                    data = AiUtils.parse_browseruse_json(result)
                except Exception as e:
                    raise ValueError(
                        f"BrowserUse retornou JSON inválido: {e} | result={result[:800]}"
                    )

                return _validate(data)

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[ScreenExplorer] Tentativa {attempt}/3 falhou: {e}"
                    + (f" — aguardando {_RETRY_DELAY_SECONDS}s antes de nova tentativa" if attempt < 3 else "")
                )
                if attempt < 3:
                    time.sleep(_RETRY_DELAY_SECONDS)

        raise ValueError(f"Falha ao obter descrições válidas do BrowserUse: {last_error}")
