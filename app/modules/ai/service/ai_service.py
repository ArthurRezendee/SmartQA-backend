import os
from sqlalchemy.ext.asyncio import AsyncSession

from browser_use import Agent, Browser, ChatBrowserUse

from app.modules.qa_analysis.service.qa_analysis_service import QaAnalysisService
from app.modules.ai.utils.ai_utils import AiUtils


class AiService:

    def __init__(self):
        self.browser = Browser(
            headless=True
        )

        self.llm = ChatBrowserUse()

    async def generate_test_cases(
        self,
        db: AsyncSession,
        analysis_id: int,
        user_id: int
    ):
        try:
            qa_service = QaAnalysisService()

            analysis = await qa_service.get_or_fail(db, analysis_id, user_id)

            credentials_block = ""

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
- Observe apenas o que está visível para o usuário
- Não execute ações adicionais além do login (se houver)

Descreva detalhadamente a interface exibida na tela.
Retorne SOMENTE a descrição da interface, sem textos adicionais.
"""

            agent = Agent(
                task=task,
                browser=self.browser,
                llm=self.llm
            )

            history = await agent.run()

            if not history or not history[-1].output:
                raise ValueError("Não foi possível obter descrição da interface")

            ui_description = history[-1].output.strip()

            prompt = AiUtils.build_test_case_prompt(
                ui_description=ui_description,
                analysis=analysis
            )

            return {
                "analysis_id": analysis_id,
                "ui_description": ui_description,
                "prompt": prompt
            }

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Erro ao gerar casos de teste: {str(e)}")
