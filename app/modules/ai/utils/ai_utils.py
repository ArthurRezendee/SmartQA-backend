from pathlib import Path
import json
import re
import ast
from typing import Any, Dict

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
        Prompt usado pelo agente BrowserUse para explorar a tela.
        Agora retorna JSON com 4 descrições em UMA explorada.
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

Seu objetivo é EXPLORAR a tela cuidadosamente e retornar QUATRO DESCRIÇÕES diferentes,
em formato JSON, que serão usadas por outros agentes do sistema:

1) tests_description: descrição técnica/funcional voltada para geração de casos de teste
2) playwright_description: descrição voltada para automação Playwright
3) documentation_description: descrição voltada para documentação funcional
4) uiux_description: avaliação crítica UI/UX com melhorias sugeridas

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

Durante a exploração, identifique e use como base:

- Estrutura geral da tela
- Elementos interativos relevantes
- Fluxos possíveis do usuário
- Comportamentos da interface
- Estados da tela (vazio, carregando, erro, sucesso)
- Limitações observáveis
- Validações e regras aparentes

==================================================
REGRAS DE SAÍDA (MUITO IMPORTANTE)
==================================================

RETORNE APENAS JSON VÁLIDO.
A RAIZ DO JSON DEVE SER UM OBJETO.
DEVE CONTER EXATAMENTE AS CHAVES ABAIXO:

{{
  "tests_description": "string",
  "playwright_description": "string",
  "documentation_description": "string",
  "uiux_description": "string"
}}

REGRAS IMPORTANTES PARA CADA CAMPO:

- tests_description:
  - descrição contínua, clara, detalhada e objetiva
  - SEM markdown, SEM listas numeradas, SEM títulos
  - SEM opinião, SEM sugestões de melhoria
  - NÃO mencione QA, testes ou agentes

- playwright_description:
  - descrição objetiva e acionável para automação
  - cite elementos e ações comuns (campos, botões, modais, tabelas, filtros, paginação)
  - sugira âncoras para seletores (label, placeholder, texto do botão)
  - SEM código
  - SEM markdown

- documentation_description:
  - linguagem clara, explicando o propósito da tela e como usar
  - descreva passos de uso e comportamentos
  - SEM markdown

- uiux_description:
  - avaliação crítica com melhorias sugeridas
  - inclua acessibilidade, consistência, hierarquia, mensagens, estados vazios/loading, prevenção de erro
  - SEM markdown
  
PROIBIDO:
- NÃO use write_file
- NÃO escreva arquivos
- NÃO use ferramentas para salvar conteúdo
- NÃO repita o JSON
- Após gerar o JSON, finalize imediatamente

NÃO inclua nenhum texto fora do JSON.
""".strip()

    @staticmethod
    def build_test_case_prompt(
        ui_description: str,
        analysis: dict,
        documents_block: str,
    ) -> str:
        """
        Prompt usado pelo agente gerador de casos de teste.
        Retorno obrigatório: JSON OBJECT com chave "items" (lista de casos).
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
    - Estados alternativos da interface (vazio, carregando, erro, sucesso)
    - Erros comuns de usuário
    - Situações limite (edge cases)
    - Regressões prováveis
    - Comportamentos que podem gerar bugs críticos

    ==================================================
    REGRAS OBRIGATÓRIAS (SEM EXCEÇÃO)
    ==================================================

    1. NÃO invente funcionalidades que não estejam descritas na interface
    2. NÃO assuma integrações externas não mencionadas
    3. NÃO descreva testes genéricos, repetidos ou vagos
    4. NÃO explique o que está fazendo
    5. NÃO utilize markdown
    6. NÃO retorne texto fora do JSON
    7. Cada caso de teste deve validar UM objetivo claro
    8. Cada passo deve representar UMA ação do usuário OU UMA verificação clara
    9. NÃO inclua comentários no JSON
    10. NÃO use chaves diferentes do formato especificado
    
    REQUISITO DE QUANTIDADE:
    - Você DEVE gerar NO MÍNIMO 40 (QUARENTA) casos de teste distintos.
    - Se a tela parecer simples, mesmo assim crie variações reais e relevantes:
    - combinações de filtros
    - paginação/ordenação
    - estados vazios
    - validações de campos
    - permissões/ações desabilitadas
    - falhas de rede/timeout
    - concorrência (alteração simultânea)
    - duplicidade
    - caracteres especiais, limites e formatos
    - Se necessário, gere 50+.

    Os testes devem cobrir:
    - Fluxos principais da tela
    - Variações válidas e inválidas de uso
    - Estados alternativos da interface (vazio, carregando, erro, sucesso)
    - Erros comuns de usuário
    - Situações limite (edge cases)
    - Regressões prováveis
    - Comportamentos que podem gerar bugs críticos

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

    RETORNE APENAS UM JSON VÁLIDO.
    A RAIZ DO JSON DEVE SER UM OBJETO (NÃO ARRAY).
    A RAIZ DEVE CONTER EXATAMENTE A CHAVE "items".

    NÃO retorne:
    - array na raiz
    - "test_cases"
    - "data"
    - "cases"
    - qualquer outra chave

    FORMATO EXATO:

    {{
    "items": [
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
    }}

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


    @staticmethod
    def parse_browseruse_json(result: str) -> Dict[str, Any]:
        """
        Faz parse robusto do retorno do BrowserUse.

        Suporta:
        - JSON normal: {"a": 1}
        - JSON escapado: {\"a\": 1}
        - string com prefixo "Final Result:" + JSON
        - JSON dentro de texto/log
        """
        if not result:
            raise ValueError("Resultado vazio do BrowserUse")

        raw = result.strip()

        # 1) tenta pegar o primeiro bloco JSON {...}
        # (isso evita lixo tipo "Final Result:" etc)
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if m:
            raw = m.group(0).strip()

        # 2) tenta JSON direto
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 3) se estiver escapado tipo {\"a\":1}
        # troca \" por "
        try:
            unescaped = raw.replace('\\"', '"')
            return json.loads(unescaped)
        except json.JSONDecodeError:
            pass

      
        try:
            evaluated = ast.literal_eval(raw)
            if isinstance(evaluated, str):
                return json.loads(evaluated)
            if isinstance(evaluated, dict):
                return evaluated
        except Exception:
            pass

        raise ValueError(f"Não foi possível parsear JSON do BrowserUse. raw={raw[:500]}")
