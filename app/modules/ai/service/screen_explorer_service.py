import asyncio
from browser_use import Agent, Browser, ChatBrowserUse

from app.modules.ai.utils.ai_utils import AiUtils


class ScreenExplorerService:
    """
    Serviço responsável por explorar a tela via BrowserUse
    e gerar a descrição funcional da interface.
    """

    def generate_ui_description(self, *, analysis: dict) -> str:
        credentials_block = AiUtils.build_credentials_block(
            analysis.get("access_credentials") or []
        )

        task = AiUtils.build_explorer_prompt(
            analysis=analysis,
            credentials_block=credentials_block,
        )

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

        return ui_description.strip()
