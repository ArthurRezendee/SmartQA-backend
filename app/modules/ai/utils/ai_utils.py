from __future__ import annotations
from pathlib import Path
import json
import re
import ast
from typing import Any, Dict, Optional
from docling.document_converter import DocumentConverter
import textwrap



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
  - Caso haja autenticacão na tela, descreva os campos para login e seus id's ou referencias.


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
    
    "{documents_block}"

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

        Robusto contra:
        - path inexistente
        - doc vazio/malformado
        - retorno sem texto
        - exceções do docling
        """

        if not documents:
            return ""

        converter = DocumentConverter()
        extracted_contents: list[str] = []

        for i, doc in enumerate(documents, start=1):
            # suporta doc como dict ou objeto
            file_path = None
            doc_type = None

            try:
                if isinstance(doc, dict):
                    file_path = doc.get("path")
                    doc_type = doc.get("type") or "Documento"
                else:
                    file_path = getattr(doc, "path", None)
                    doc_type = getattr(doc, "type", None) or "Documento"
            except Exception:
                extracted_contents.append(
                    f"--- DOCUMENTO {i} ---\nDocumento inválido (estrutura inesperada)."
                )
                continue

            if not file_path:
                extracted_contents.append(
                    f"--- {str(doc_type).upper()} ---\nDocumento sem caminho (path vazio)."
                )
                continue

            path = Path(file_path)

            if not path.exists():
                extracted_contents.append(
                    f"--- {str(doc_type).upper()} ---\nArquivo não encontrado: {file_path}"
                )
                continue

            if not path.is_file():
                extracted_contents.append(
                    f"--- {str(doc_type).upper()} ---\nPath não é arquivo: {file_path}"
                )
                continue

            try:
                result = converter.convert(str(path))
                text = (result.document.export_to_text() or "").strip()

                if not text:
                    extracted_contents.append(
                        f"--- {str(doc_type).upper()} ---\n"
                        f"Não foi possível extrair texto (arquivo pode ser imagem/escaneado). "
                        f"Arquivo: {path.name}"
                    )
                    continue

                # (opcional) limitar tamanho para não explodir o prompt
                MAX_CHARS = 12000
                if len(text) > MAX_CHARS:
                    text = text[:MAX_CHARS] + "\n\n[...texto truncado...]"

                extracted_contents.append(
                    f"--- {str(doc_type).upper()} ({path.suffix.lower()}) ---\n{text}"
                )

            except Exception as e:
                extracted_contents.append(
                    f"--- {str(doc_type).upper()} ---\nErro ao processar documento: {type(e).__name__}"
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


    def build_playwright_script_prompt(analysis: Dict[str, Any]) -> str:
        """
        Monta um prompt robusto para um agente gerar scripts Playwright
        usando os dados de uma QaAnalysis (1 objeto).

        Espera chaves como:
        - id
        - name
        - target_url
        - description
        - screen_context
        - tests_description
        - playwright_description
        - documentation_description
        - uiux_description

        Retorna: string prompt
        """
        
        credentials_block = AiUtils.build_credentials_block(
            analysis.get("access_credentials") or []
        )

        # Helpers pra evitar "None" no prompt
        def s(value: Optional[Any], fallback: str = "") -> str:
            if value is None:
                return fallback
            v = str(value).strip()
            return v if v else fallback

        analysis_id = s(analysis.get("id"), "N/A")
        name = s(analysis.get("name"), "Sem nome")
        target_url = s(analysis.get("target_url"), "")
        description = s(analysis.get("description"), "")
        screen_context = s(analysis.get("screen_context"), "")
        playwright_description = s(analysis.get("playwright_description"), "")
        tests_description = s(analysis.get("tests_description"), "")
        documentation_description = s(analysis.get("documentation_description"), "")
        uiux_description = s(analysis.get("uiux_description"), "")

        # Regra especial: se não tiver target_url, não faz sentido gerar script
        if not target_url:
            raise ValueError("analysis.target_url é obrigatório para gerar script Playwright")

        prompt = f"""
    Você é um Engenheiro de QA Automation Sênior especialista em Playwright.

    Você deve gerar um script Playwright COMPLETO e EXECUTÁVEL para automatizar testes E2E
    da tela descrita abaixo, seguindo fielmente o contexto fornecido.

    ==================================================
    DADOS DA ANÁLISE
    ==================================================

    analysis_id: {analysis_id}
    name: {name}
    target_url: {target_url}

    Objetivo definido pelo QA:
    "{description or "Não informado."}"

    Contexto da tela:
    "{screen_context or "Não informado."}"

    ==================================================
    DESCRIÇÃO PARA AUTOMAÇÃO (FONTE PRINCIPAL)
    ==================================================

    Use esta descrição como BASE para seletores e fluxos:

    \"\"\"
    {playwright_description or "Não informado."}
    \"\"\"

    ==================================================
    DESCRIÇÃO FUNCIONAL (APOIO)
    ==================================================

    \"\"\"
    {tests_description or "Não informado."}
    \"\"\"

    ==================================================
    DOCUMENTAÇÃO (APOIO)
    ==================================================

    \"\"\"
    {documentation_description or "Não informado."}
    \"\"\"

    ==================================================
    OBSERVAÇÕES UI/UX (APOIO)
    ==================================================

    \"\"\"
    {uiux_description or "Não informado."}
    \"\"\"

    ==================================================
    OBJETIVO DO SCRIPT
    ==================================================

    Gerar um arquivo de teste Playwright que:

    1) Acesse a URL {target_url}
    2) Execute os fluxos principais da tela
    3) Valide listagem, filtros e paginação (quando existirem)
    4) Valide criação e edição/atualização (quando existirem)
    5) Cubra validações de campos obrigatórios e entradas inválidas
    6) Gere asserts realistas e estáveis
    7) NÃO teste funcionalidades proibidas pelo QA (se houver)

    ==================================================
    REGRAS IMPORTANTES (OBRIGATÓRIO)
    ==================================================

    - Gere testes com Playwright Test Runner (@playwright/test)
    - Use TypeScript por padrão
    - Use seletores estáveis:
    - priorize getByRole(), getByLabel(), getByPlaceholder(), getByText()
    - se necessário use locator('#id') conforme indicado na descrição
    - Evite seletores frágeis (css baseado em nth-child, classes dinâmicas, etc)
    - Inclua waits inteligentes:
    - aguarde navegação e carregamento
    - evite timeouts fixos (waitForTimeout) a menos que seja inevitável
    - Separe testes em blocos `test.describe`
    - Use `beforeEach` para login/navegação se fizer sentido
    - Não invente elementos que não existem na descrição
    - Caso algum passo seja incerto, implemente fallback com tentativas seguras e asserts suaves
    - Se houver modais, valide abertura e fechamento
    - Se houver paginação, valide troca de limite (10/50/100/1000) quando aplicável

    ==================================================
    RESTRIÇÕES DO QA
    ==================================================

    Se no objetivo existir alguma restrição como:
    "Precisa testar tudo na tela, menos o botão de importar"

    Então:
    - NÃO clique no botão proibido
    - NÃO crie teste envolvendo esse fluxo

    ==================================================
    FORMATO DE SAÍDA (MUITO IMPORTANTE)
    ==================================================

    RETORNE APENAS JSON VÁLIDO.
    A raiz deve ser um OBJETO com EXATAMENTE as chaves:

    {{
    "language": "typescript",
    "framework": "playwright",
    "title": "string",
    "script": "string"
    }}

    REGRAS DO CAMPO script:
    - deve conter o código COMPLETO do arquivo `.spec.ts`
    - não use markdown
    - não inclua explicações
    - não inclua texto fora do JSON

    ==================================================
    CHECKLIST DE QUALIDADE (OBRIGATÓRIO)
    ==================================================

    Antes de finalizar, garanta que:
    - o código compila
    - imports estão corretos
    - o script não tem placeholders do tipo TODO
    - os testes têm asserts (expect)
    - os testes são resilientes a loading e estados iniciais
    """.strip()

        return textwrap.dedent(prompt).strip()
