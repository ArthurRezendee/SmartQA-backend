from agno.agent import Agent
from agno.models.openai import OpenAIChat


class TestCaseAgent:

    def __init__(self):
        self.agent = Agent(
            model=OpenAIChat(
                model="gpt-4o-mini",
                temperature=0.2
            ),
            system_prompt=f"Você é um QA Sênior altamente experiente, especializado em testes funcionais, regressão e prevenção de bugs críticos em sistemas web."
        )

    def generate(self, prompt: str) -> dict:
        response = self.agent.run(prompt)
        return response
