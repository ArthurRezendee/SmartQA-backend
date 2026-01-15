import os
from openai import OpenAI

class TestCaseAgent:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não definida no ambiente")

        self.client = OpenAI(api_key=api_key)

    def generate(self, prompt: str) -> str:
        system_prompt = (
            "Você é um QA Sênior altamente experiente, especializado em "
            "testes funcionais, testes de regressão, testes exploratórios "
            "e prevenção de bugs críticos em sistemas web e APIs."
        )

        full_prompt = f"""
REGRA CRÍTICA:
- Gere O MÁXIMO DE CASOS DE TESTE POSSÍVEL
- NÃO pare até esgotar TODOS os cenários observáveis da interface
- Priorize QUANTIDADE sem perder clareza
- Cada caso de teste deve ser ÚNICO
- Cubra fluxos felizes, alternativos, erros, bordas e abusos
- Utilize linguagem clara, objetiva e técnica

CONTEXTO DO SISTEMA:
{prompt}
"""

        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",  # pode trocar se quiser
            temperature=0.4,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt},
            ],
        )

        return response.choices[0].message.content
