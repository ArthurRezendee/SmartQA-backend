class AiUtils:

    @staticmethod
    def build_test_case_prompt(ui_description: str, analysis: dict) -> str:
        return f"""
Você é um QA Sênior especialista em testes funcionais de sistemas web.

Você está trabalhando em uma análise de QA com o seguinte contexto:

Nome da análise:
"{analysis.get("name")}"

URL do sistema:
{analysis.get("target_url")}

Objetivo da análise (descrição fornecida pelo QA):
"{analysis.get("description")}"

Sua tarefa é gerar CASOS DE TESTE FUNCIONAIS com base:
- No objetivo da análise
- E EXCLUSIVAMENTE nos elementos e comportamentos descritos na interface analisada

⚠️ Regras obrigatórias:
- NÃO invente funcionalidades que não apareçam na descrição da interface
- Priorize casos de teste diretamente relacionados ao objetivo da análise
- Gere casos de teste claros, objetivos e realistas
- Inclua casos positivos e negativos
- Pense como um QA que quer prevenir bugs críticos
- Os casos devem ser facilmente revisáveis por um humano
- NÃO escreva textos explicativos fora do formato solicitado

Formato de saída:
- Retorne APENAS um JSON válido
- Não inclua comentários, textos extras ou markdown

Formato do JSON esperado:

[
  {{
    "title": "Título claro e objetivo do caso de teste",
    "preconditions": "Condições necessárias antes da execução",
    "steps": [
      "Passo 1",
      "Passo 2",
      "Passo 3"
    ],
    "expected_result": "Resultado esperado ao final do teste",
    "type": "positive | negative"
  }}
]

Descrição da interface analisada:
\"\"\"
{ui_description}
\"\"\"
"""
