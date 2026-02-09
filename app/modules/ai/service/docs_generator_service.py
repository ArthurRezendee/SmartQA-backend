import os
from openai import OpenAI


class DocumentationAgent:
    def __init__(self, model: str):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não definida")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um Analista de Sistemas Sênior especializado "
                        "em documentação funcional de software."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()
