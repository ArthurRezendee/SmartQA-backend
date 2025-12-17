class AiUtils:

    @staticmethod
    def build_test_case_prompt(ui_description: str, analysis: dict) -> str:
        return f"""
Você é um QA Sênior altamente experiente, especializado em testes funcionais,
regressão e prevenção de bugs críticos em sistemas web.

Você está executando uma ANÁLISE DE QA com o seguinte contexto:

Nome da análise:
"{analysis.get("name")}"

URL do sistema:
{analysis.get("target_url")}

Objetivo da análise (fornecido pelo QA):
"{analysis.get("description")}"

Contexto adicional da tela:
"{analysis.get("screen_context")}"

==================================================
TAREFA PRINCIPAL
==================================================

Gerar o MAIOR NÚMERO POSSÍVEL de CASOS DE TESTE FUNCIONAIS
com base EXCLUSIVAMENTE na interface analisada.

Os testes devem cobrir:
- Fluxos principais da tela
- Variações válidas e inválidas de uso
- Estados alternativos da interface
- Erros comuns de usuário
- Situações limite (edge cases)
- Regressões prováveis
- Comportamentos que podem gerar bugs críticos

==================================================
REGRAS OBRIGATÓRIAS
==================================================

1. NÃO invente funcionalidades que não estejam descritas na interface
2. NÃO assuma integrações externas não mencionadas
3. NÃO descreva testes genéricos ou repetidos
4. NÃO explique o que está fazendo
5. NÃO utilize markdown ou texto fora do JSON
6. Cada caso de teste deve validar UM objetivo claro
7. Cada passo deve representar UMA ação do usuário ou UMA verificação clara
8. Pense como um QA experiente tentando QUEBRAR o sistema

==================================================
DIVERSIDADE DE TESTES (OBRIGATÓRIO)
==================================================

Distribua os testes entre os seguintes tipos, quando aplicável:

- functional
- regression
- smoke
- exploratory

Distribua os cenários entre:

- positive
- negative
- edge

Use prioridade e risco de forma REALISTA:
- critical → falha bloqueia uso da tela
- high → falha grave, mas com workaround
- medium → impacto parcial
- low → impacto visual ou secundário

==================================================
FORMATO DE SAÍDA (OBRIGATÓRIO)
==================================================

Retorne APENAS um JSON válido no formato abaixo.
Não inclua comentários, explicações ou texto extra.

[
  {{
    "title": "Título curto, claro e objetivo",
    "description": "Descrição do cenário validado pelo teste",
    "objective": "O que este teste garante no sistema",

    "test_type": "functional | regression | smoke | exploratory",
    "scenario_type": "positive | negative | edge",
    "priority": "low | medium | high | critical",
    "risk_level": "low | medium | high",

    "preconditions": "Condições necessárias antes da execução",
    "expected_result": "Resultado esperado ao final do cenário",

    "steps": [
      {{
        "order": 1,
        "action": "Ação realizada pelo usuário",
        "expected_result": "Resultado esperado após a ação"
      }},
      {{
        "order": 2,
        "action": "Ação realizada pelo usuário",
        "expected_result": "Resultado esperado após a ação"
      }}
    ]
  }}
]

==================================================
DESCRIÇÃO DA INTERFACE ANALISADA
==================================================

\"\"\"
{ui_description}
\"\"\"
"""
