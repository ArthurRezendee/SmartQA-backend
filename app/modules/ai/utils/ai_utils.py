# from docling.document_converter import DocumentConverter
from pathlib import Path

class AiUtils:
    """
    Utilitários de IA responsáveis por construir prompts e blocos de contexto.
    Toda regra de negócio relacionada a PROMPTS deve ficar aqui.
    """

    @staticmethod
    def build_credentials_block(access_credentials: list[dict]) -> str:
        """
        Gera o bloco de instruções de autenticação para o agente BrowserUse.
        """
        if not access_credentials:
            return (
                "Caso a tela não exija autenticação, apenas acesse a página normalmente.\n"
            )

        block = "Realize o login seguindo exatamente os passos abaixo:\n"

        for cred in access_credentials:
            field = cred.get("field_name")
            value = cred.get("value")

            if field and value:
                block += f'- Preencha o campo "{field}" com o valor "{value}".\n'

        return block

    @staticmethod
    def build_explorer_prompt(
        *,
        analysis: dict,
        credentials_block: str,
    ) -> str:
        """
        Prompt usado pelo agente BrowserUse para gerar a descrição funcional da tela.
        """

        return f"""
Acesse a URL abaixo:
{analysis["target_url"]}

{credentials_block}

==================================================
CONTEXTO ADICIONAL FORNECIDO PELO QA
==================================================

Use as informações abaixo para entender a regra de negócio da tela e
GUIAR a exploração, evitando interações desnecessárias.

{analysis.get("screen_context") or "Nenhum contexto adicional fornecido."}

==================================================
OBJETIVO DA EXPLORAÇÃO
==================================================

Você está atuando como um QA Sênior especializado em testes funcionais de interfaces web.

Seu objetivo é EXPLORAR a tela cuidadosamente e produzir uma DESCRIÇÃO TÉCNICA E FUNCIONAL
da interface, que será usada por outro agente para GERAR CASOS DE TESTE.

==================================================
REGRAS DE EXPLORAÇÃO
==================================================

- NÃO saia da tela atual (não navegue para outras URLs)
- Explore SOMENTE o que é acessível a partir desta tela
- Priorize a exploração dos fluxos e regras mencionados no contexto do QA
- Evite explorar elementos irrelevantes ao objetivo da tela
- Interaja com botões, abas, campos, modais e menus quando forem relevantes
- Observe comportamentos normais e comportamentos inesperados
- Identifique estados diferentes da interface (ex: vazio, carregando, erro, sucesso)

==================================================
O QUE DESCREVER (OBRIGATÓRIO)
==================================================

Durante a exploração, descreva claramente:

1. Estrutura geral da tela
2. Elementos interativos relevantes
3. Fluxos possíveis do usuário
4. Comportamentos da interface
5. Estados da tela
6. Limitações observáveis

==================================================
REGRAS DE SAÍDA
==================================================

- NÃO explique o que você está fazendo
- NÃO inclua opiniões pessoais
- NÃO use markdown, listas numeradas ou títulos
- NÃO inclua textos fora da descrição da interface
- NÃO mencione QA, testes ou agentes

Retorne APENAS uma descrição contínua, clara, detalhada e objetiva da interface explorada,
como se estivesse documentando a tela para alguém que nunca a viu.
""".strip()

    @staticmethod
    def build_test_case_prompt(ui_description: str, analysis: dict, documents_block: str,) -> str:
        """
        Prompt usado pelo agente gerador de casos de teste.
        """

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
""".strip()

    @staticmethod
    def read_documents_with_docling(documents: list) -> str:
        """
        Lê documentos da qa_documents usando Docling
        e retorna um texto unificado para RAG no prompt.
        """

        if not documents:
            return ""

        converter = DocumentConverter()
        extracted_contents: list[str] = []

        for doc in documents:
            file_path = doc.path
            doc_type = doc.type or "Documento"

            if not file_path or not Path(file_path).exists():
                continue

            try:
                result = converter.convert(file_path)
                text = result.document.export_to_text()

                if text:
                    extracted_contents.append(
                        f"--- {doc_type.upper()} ---\n{text.strip()}"
                    )

            except Exception:
                extracted_contents.append(
                    f"--- {doc_type.upper()} ---\nErro ao processar o documento."
                )

        return "\n\n".join(extracted_contents)
      
    @staticmethod
    def build_documents_block(documents_text: str) -> str:
        """
        Gera o bloco de contexto documental para o prompt.
        """

        if not documents_text:
            return "Nenhum documento adicional foi fornecido pelo QA."

        return f"""
==================================================
DOCUMENTAÇÃO ANEXADA À ANÁLISE
==================================================

Os textos abaixo foram extraídos de documentos fornecidos pelo QA.

Use essas informações apenas para:
- entender regras de negócio
- compreender validações
- alinhar nomenclaturas e fluxos

REGRAS IMPORTANTES:
- NÃO invente funcionalidades
- NÃO gere testes baseados apenas no documento
- Se houver conflito, PRIORIZE a interface analisada

{documents_text}
""".strip()