from __future__ import annotations
from pathlib import Path
import json
import re
import ast
from typing import Any, Dict, Optional
from docling.document_converter import DocumentConverter
import textwrap


def _sanitize_json_strings(s: str) -> str:
    """
    Percorre o JSON char a char e escapa newlines/tabs/CR literais que aparecem
    dentro de valores de string. LLMs às vezes emitem \n real em vez de \\n.
    """
    result = []
    in_string = False
    escaped = False
    for ch in s:
        if escaped:
            result.append(ch)
            escaped = False
        elif ch == "\\":
            result.append(ch)
            escaped = True
        elif ch == '"':
            in_string = not in_string
            result.append(ch)
        elif in_string and ch == "\n":
            result.append("\\n")
        elif in_string and ch == "\r":
            result.append("\\r")
        elif in_string and ch == "\t":
            result.append("\\t")
        else:
            result.append(ch)
    return "".join(result)


class AiUtils:
    """
    Utilitários de IA responsáveis por construir prompts e blocos de contexto.
    Toda regra de negócio relacionada a PROMPTS deve ficar aqui.
    """

    @staticmethod
    def build_credentials_block(access_credentials: list[dict], target_url: str = "") -> str:
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

        if target_url:
            block += (
                f'\nApós o login, se for redirecionado para outra página, '
                f'navegue para a URL alvo: {target_url}\n'
            )

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
Acesse a URL alvo:
{analysis["target_url"]}

{credentials_block}

==================================================
CONTEXTO ADICIONAL FORNECIDO PELO QA
==================================================

{analysis.get("screen_context") or "Nenhum contexto adicional fornecido."}

==================================================
PASSO 1 — MAPEAMENTO OBRIGATÓRIO (FAÇA ANTES DE QUALQUER OUTRA COISA)
==================================================

Antes de escrever qualquer descrição, execute a sequência abaixo:

1. Role a página do TOPO ao FUNDO completamente (use scroll até não aparecer mais conteúdo novo).
2. Registre mentalmente CADA SEÇÃO visível pelo seu TÍTULO EXATO como aparece na tela
   (ex: "Como funciona", "Planos e preços", "Depoimentos", "FAQ", "Entre em contato").
3. Para cada seção, anote: título exato, conteúdo principal, elementos interativos presentes.
4. Expanda accordions, abas, carrosséis, menus, dropdowns e modais que existirem.
5. Identifique e anote os textos exatos de todos os botões de ação (CTA).
6. Anote todos os campos de formulário com seus labels/placeholders exatos.
7. NÃO avance para escrever os campos do JSON até ter feito este mapeamento completo.

==================================================
OBJETIVO DA EXPLORAÇÃO
==================================================

Você está atuando como um QA Sênior especializado em testes funcionais de interfaces web.

Seu objetivo é EXPLORAR a tela de forma EXAUSTIVA e retornar QUATRO DESCRIÇÕES diferentes,
em formato JSON, usadas por outros agentes do sistema.

==================================================
REGRAS DE EXPLORAÇÃO
==================================================

- Após acessar (e realizar login se necessário), permaneça na URL alvo e NÃO navegue para outras URLs
- Role a página INTEIRA antes de descrever qualquer coisa
- Interaja com TODOS os elementos interativos relevantes: abas, accordions, carrosséis, filtros, modais
- Registre o TEXTO EXATO de títulos, botões, labels e placeholders — nunca parafaseie
- Observe e descreva estados distintos da interface (vazio, carregando, erro, sucesso)
- NÃO assuma o que a tela faz — descreva SOMENTE o que foi realmente observado

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

REGRAS PARA CADA CAMPO:

- tests_description:
  - Descreva CADA SEÇÃO da tela separadamente, na ordem em que aparece.
  - Para cada seção: nome exato, propósito, elementos interativos, comportamentos observados.
  - Inclua: fluxos possíveis, validações visíveis, estados da interface, edge cases observáveis.
  - SEM markdown, SEM listas numeradas, SEM títulos no texto.
  - SEM opinião, SEM sugestões de melhoria, NÃO mencione QA ou agentes.

- playwright_description:
  - Liste cada elemento interativo com: tipo, texto/label/placeholder EXATO, atributos id/name/aria quando visíveis.
  - Para botões: texto exato do botão.
  - Para campos: label exato e placeholder exato.
  - Para links: texto exato e destino se visível.
  - Para formulários: todos os campos, validações visíveis, botão de submit.
  - Se houver login: descreva campos e referências de seletor.
  - Estruture como inventário de elementos por seção da tela.

- documentation_description:
  - Liste TODAS as seções da página pelo TÍTULO EXATO que aparece na tela, na ordem de aparição.
  - Para cada seção: título exato, o que ela contém, quem é o público-alvo daquela seção.
  - Descreva os fluxos de uso reais que um usuário executaria nesta tela.
  - SEM markdown. Baseie-se 100% no que foi observado — ZERO invenção.

- uiux_description:
  - Avaliação crítica com base no que foi realmente observado.
  - Inclua: acessibilidade, hierarquia visual, consistência, mensagens de feedback, estados vazios/loading, prevenção de erros.
  - Cite elementos ESPECÍFICOS da tela ao fazer críticas.
  - SEM markdown.

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

        objective = (analysis.get("description") or "").strip()
        objective_block = f"""
    ==================================================
    ESCOPO RESTRITO — LEIA ANTES DE QUALQUER COISA
    ==================================================

    O QA definiu um objetivo específico para esta análise:
    "{objective}"

    REGRA ABSOLUTA DE ESCOPO:
    - Gere casos de teste SOMENTE para o que está descrito no objetivo acima.
    - Se o objetivo citar uma aba, funcionalidade, fluxo ou elemento específico,
      ignore completamente todos os outros elementos da interface.
    - Esta restrição tem PRIORIDADE MÁXIMA sobre qualquer outra instrução deste prompt.
    - NÃO amplie o escopo, mesmo que a interface tenha outras funcionalidades relevantes.
""" if objective else ""

        return f"""
    Você é um QA Sênior altamente experiente, especializado em testes funcionais,
    regressão e prevenção de bugs críticos em sistemas web.
    {objective_block}
    Você está executando uma ANÁLISE DE QA com o seguinte contexto:

    Nome da análise:
    "{analysis.get("name")}"

    URL do sistema:
    {analysis.get("target_url")}

    Objetivo da análise (fornecido pelo QA):
    "{objective or "Não informado — cubra toda a interface descrita abaixo."}"

    Contexto adicional da tela:
    "{analysis.get("screen_context")}"

    "{documents_block}"

    ==================================================
    TAREFA PRINCIPAL
    ==================================================

    Gerar CASOS DE TESTE FUNCIONAIS com base EXCLUSIVAMENTE na interface analisada,
    respeitando o escopo definido no objetivo acima.

    Os testes devem cobrir (dentro do escopo):
    - Fluxos principais
    - Variações válidas e inválidas de uso
    - Estados alternativos da interface (vazio, carregando, erro, sucesso)
    - Erros comuns de usuário
    - Situações limite (edge cases)
    - Regressões prováveis

    ==================================================
    REGRAS OBRIGATÓRIAS (SEM EXCEÇÃO)
    ==================================================

    1. NÃO invente funcionalidades — cada teste deve referenciar explicitamente um elemento,
       ação ou comportamento DESCRITO na interface abaixo.
    2. NÃO assuma integrações externas não mencionadas.
    3. NÃO descreva testes genéricos sem ancoragem na interface real.
       ERRADO: "Verificar que a página carrega corretamente."
       CERTO: "Verificar que a seção 'Como funciona' exibe os 3 passos ao acessar a página."
    4. NÃO explique o que está fazendo.
    5. NÃO utilize markdown.
    6. NÃO retorne texto fora do JSON.
    7. Cada caso de teste deve validar UM objetivo claro e específico.
    8. Cada passo deve referenciar UM elemento REAL da interface (pelo nome/label observado).
    9. NÃO inclua comentários no JSON.
    10. NÃO use chaves diferentes do formato especificado.

    ÂNCORAGEM OBRIGATÓRIA:
    - Cada título de teste deve mencionar o ELEMENTO ou SEÇÃO REAL envolvido.
    - Cada step "action" deve mencionar o ELEMENTO EXATO sendo manipulado (ex: botão "Começar agora", campo "E-mail", seção "Planos").
    - Se a interface não possui um determinado elemento, NÃO crie testes para ele.

    REQUISITO DE COBERTURA (OBRIGATÓRIO):
    Esgote todos os cenários que a interface suporta dentro do escopo.
    Para cada elemento real da interface, cubra:
    - Cada seção/bloco individualmente
    - Cada botão de ação: o que acontece ao clicar
    - Cada campo de formulário: preenchimento válido, inválido e vazio
    - Cada fluxo completo do usuário (do início ao fim)
    - Cada estado distinto observado (vazio, com dados, carregando, erro, sucesso)
    - Cada edge case baseado em comportamento OBSERVADO

    Se a interface é rica, 30-50+ casos são esperados e desejados.
    Se a interface é simples, gere somente os casos realmente aplicáveis.
    NÃO repita casos com variações mínimas.
    NÃO crie casos para elementos inexistentes na interface.

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
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if m:
            raw = m.group(0).strip()

        # 2) tenta JSON direto
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 3) sanitiza newlines/tabs literais dentro de strings JSON e tenta novamente
        # (LLMs às vezes emitem \n real em vez de \\n dentro dos valores)
        try:
            return json.loads(_sanitize_json_strings(raw))
        except json.JSONDecodeError:
            pass

        # 4) se estiver escapado tipo {\"a\":1}, desfaz e tenta
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


    @staticmethod
    def build_stress_test_prompt(*, analysis: dict, credentials_block: str) -> str:
        target_url = analysis.get("target_url", "")
        description = (analysis.get("description") or "").strip()
        screen_context = (analysis.get("screen_context") or "").strip()
        target_name = (analysis.get("name") or "").strip()
        tests_description = (analysis.get("tests_description") or "").strip()

        scope_block = f"""
==================================================
ESCOPO DO STRESS TEST
==================================================
Alvo: {target_name}
URL: {target_url}
Objetivo definido pelo QA: "{description or 'Cobrir toda a interface'}"
Contexto adicional: "{screen_context or 'Não informado'}"
""".strip()

        knowledge_block = f"""
==================================================
CONHECIMENTO PRÉVIO DA INTERFACE
==================================================
Use como referência para identificar elementos, mas NÃO deixe isso limitar os ataques.
{tests_description}
""".strip() if tests_description else ""

        return f"""
MISSÃO: STRESS TEST BRUTO — QUEBRE ESTA TELA.

Você é um QA Sênior especialista em stress testing, segurança web e caça de bugs.
Sua missão é DESTRUIR sistematicamente esta interface. Não tenha misericórdia.
Teste CADA elemento. Tente CADA input possível. Documente TUDO que quebrar.

{scope_block}

{credentials_block}

{knowledge_block}

==================================================
PROTOCOLO OBRIGATÓRIO DE DESTRUIÇÃO SISTEMÁTICA
==================================================

FASE 0 — CARREGAMENTO DA PÁGINA
Esta é uma SPA que pode demorar para renderizar. Siga exatamente:
1. Navegue para a URL e IMEDIATAMENTE execute wait de 20 segundos.
2. Verifique se há conteúdo. Se sim: prossiga. Se ainda vazio: navegue para a URL novamente e execute wait de 20 segundos.
3. Se ainda vazio após a segunda tentativa: navegue para a URL uma terceira vez e execute wait de 20 segundos.
4. Se após as 3 tentativas (cada uma com navigate + wait 20s na MESMA URL) ainda não carregar: registre finding (severity: critical, category: crash) com título "Página não carrega após 60 segundos" e encerre o teste.
NUNCA tente paths alternativos (/login, /auth, etc) — use sempre exatamente a URL fornecida.
Se aparecer spinner ou loading animado: aguarde ele sumir antes de agir — isso é SPA carregando normalmente.

REGRA DE TELA-ALVO — LEIA ANTES DE QUALQUER FASE:
A tela que você deve atacar é SEMPRE a URL fornecida no escopo. Nunca desvie para testar outras telas do sistema.

Se credenciais foram fornecidas, o único propósito delas é:
  a) confirmar que o login válido funciona (registre como finding se falhar)
  b) acessar a tela-alvo caso ela exija autenticação prévia

Após qualquer ação bem-sucedida (login, submit, redirecionamento), VOLTE para a URL da tela-alvo e continue os ataques lá. Não siga para as telas internas do sistema.

Exemplo: se a URL-alvo é uma tela de login, faça o login com credenciais válidas para confirmar o happy path, depois navegue DE VOLTA para a URL de login e execute todos os ataques no formulário de login. Os ataques são na tela de login, não na tela que aparece depois.

REGRA DE CONTINUIDADE — NUNCA PARE:
Você deve encontrar TODOS os bugs, não apenas o primeiro. Independente do resultado de cada teste individual:
- Se um ataque não produz resposta visível: documente se for o caso e PROSSIGA para o próximo ataque
- Se uma ação travar a tela: aguarde, recarregue se necessário, e CONTINUE os próximos testes
- Se o login falhar: registre como finding e CONTINUE testando os demais ataques no formulário
- Nunca encerre o teste antes de ter executado todos os ataques em todos os elementos mapeados
- Entregue TODOS os findings acumulados no JSON final

FASE 1 — RECONHECIMENTO E INVENTÁRIO OBRIGATÓRIO
- Navegue para a URL-alvo
- Se necessário, use as credenciais fornecidas para acessar a tela (e volte para ela após o login)
- Mapeie e LISTE EXPLICITAMENTE todos os elementos interativos encontrados:
  * CAMPOS: liste cada campo de texto/input/textarea pelo nome/label exato (ex: "Campo Login", "Campo Senha", "Campo E-mail")
  * BOTÕES: liste cada botão pelo texto exato (ex: "Botão Entrar", "Botão Cancelar")
  * OUTROS: dropdowns, checkboxes, links, tabs — liste pelo label/texto exato

ATENÇÃO: Esta lista é o seu CONTRATO. Você deve atacar CADA elemento desta lista antes de encerrar.
Você NÃO pode pular nenhum elemento. Você NÃO pode encerrar antes de atacar todos.

FASE 2 — ATAQUE SISTEMÁTICO A INPUTS
LOOP OBRIGATÓRIO: Para cada campo de texto/input/textarea da lista da Fase 1, execute TODOS os 16 ataques abaixo.
Finalize os 16 ataques no Campo 1 antes de começar o Campo 2. Finalize os 16 no Campo 2 antes de começar o Campo 3. E assim por diante.
Após completar os 16 ataques em um campo, recarregue a página (ou navegue novamente para a URL-alvo) para resetar o estado antes do próximo campo.

NUNCA avance para a Fase 3 sem ter executado TODOS os 16 ataques em TODOS os campos da lista.

1. Envio vazio — clique no submit sem preencher o campo
2. Apenas espaços em branco: "   "
3. String gigante: "A" repetido 5000 vezes
4. XSS básico: <script>alert('XSS')</script>
5. XSS alternativo: <img src=x onerror=alert(1)>
6. SQL Injection: ' OR '1'='1'; DROP TABLE users;--
7. Caracteres especiais: !@#$%^&*()_+-=[]{{}}|;':",.<>?/~`\\
8. Emojis e unicode: 🔥💀👾💥 αβγδ 中文 العربية Ñoño
9. Número negativo: -999999
10. Zero: 0
11. Float enorme: 99999999.9999999
12. Data inválida: 99/99/9999
13. E-mail inválido: nao@@email..com
14. Booleano como texto: true / false / null / undefined
15. Só ponto: .....
16. Quebra de linha como input: use o caractere de nova linha

CONFIRMAÇÃO FASE 2: Você só pode avançar para a Fase 3 após confirmar internamente que executou os 16 ataques em CADA campo da lista.

FASE 3 — ATAQUE A BOTÕES E AÇÕES
LOOP OBRIGATÓRIO: Para CADA botão da lista da Fase 1, execute TODOS os testes abaixo:
- Clique sem preencher os campos obrigatórios vinculados
- Clique múltiplas vezes consecutivas rapidamente
- Busque e execute botões de delete/remover/cancelar em itens existentes
- Teste botões de confirmação (sim/não, confirmar/cancelar) em estados inesperados

NUNCA avance para a Fase 4 sem ter testado TODOS os botões da lista.

FASE 4 — ATAQUE A FLUXOS E ESTADO
- Preencha formulário pela metade, use o botão voltar do browser, volte à página e tente submeter
- Submeta o mesmo formulário duas vezes seguidas (duplo envio)
- Altere parâmetros de ID na URL (ex: troque /item/1 por /item/999999, /item/-1, /item/abc)
- Tente acessar rotas de admin ou áreas restritas diretamente na URL
- Abra links em estado não logado adicionando ?auth=bypass na URL

FASE 5 — DETECÇÃO ATIVA DE ERROS
Em CADA interação, observe e documente qualquer um destes sinais de bug:
- Mensagens de erro genéricas expostas: "500", "Internal Server Error", "Undefined", stack trace visível
- Campo que aceita valor claramente inválido sem nenhuma mensagem de erro
- Campo que rejeita valor válido com mensagem de erro incorreta
- Spinner/loading que não termina (aguarde 8 segundos)
- Modal que não fecha ou fica travado
- Layout quebrado após uma ação (elementos sobrepostos, texto cortado, seção desaparece)
- Debug info, IDs internos, caminhos de arquivo ou stack traces expostos ao usuário
- Ação que executa silenciosamente sem nenhum feedback (sucesso ou erro)
- Botão que não responde ao clique
- Redirecionamento inesperado para página errada ou em branco
- Dados que somem após salvar (salva mas não mostra, ou volta ao valor anterior)
- Comportamento inconsistente: funciona uma vez, não funciona na segunda

==================================================
VERIFICAÇÃO FINAL OBRIGATÓRIA (ANTES DE GERAR O JSON)
==================================================

Antes de retornar o JSON, confirme cada item da lista abaixo.
Se algum item não foi completado, execute-o AGORA antes de gerar o JSON.

Para CADA campo de texto/input listado na Fase 1:
[ ] Executei os 16 ataques (ataques 1 a 16)

Para CADA botão listado na Fase 1:
[ ] Testei clique sem campos preenchidos
[ ] Testei cliques múltiplos consecutivos

Somente gere o JSON após confirmar que TODOS os elementos foram atacados.

==================================================
REGRAS CRÍTICAS
==================================================
1. DOCUMENTE APENAS O QUE REALMENTE OBSERVAR — nunca invente bugs
2. Se o sistema se comportou CORRETAMENTE com o input inválido, NÃO documente como bug
3. Seja ESPECÍFICO: "Campo 'Email' aceitou string de 5000 chars sem truncar ou mostrar erro" é melhor que "campo tem bug"
4. Cubra 100% dos elementos interativos visíveis na tela
5. Tire screenshot IMEDIATAMENTE ao detectar qualquer anomalia
6. Não pare até ter testado TODOS os elementos mapeados na Fase 1

==================================================
FORMATO DE SAÍDA OBRIGATÓRIO
==================================================

Retorne APENAS JSON válido. Nenhum texto fora do JSON.

{{
  "summary": "Resumo executivo em 3-4 frases: quantos bugs foram encontrados, quais as categorias mais críticas e qual o impacto geral na aplicação.",
  "total_findings": N,
  "findings": [
    {{
      "order": 1,
      "title": "Título conciso e objetivo do bug",
      "description": "Descrição precisa do que aconteceu e qual o impacto",
      "severity": "critical",
      "category": "security",
      "element": "Nome ou descrição exata do elemento testado (ex: Campo 'E-mail' no formulário de login)",
      "input_used": "Valor exato inserido ou ação exata realizada",
      "steps_to_reproduce": [
        "Passo 1: Acesse a URL X",
        "Passo 2: Insira no campo 'Y' o valor 'Z'",
        "Passo 3: Clique no botão 'Salvar'",
        "Passo 4: Observe que [comportamento observado]"
      ],
      "error_details": "Mensagem de erro exata que apareceu na tela, ou 'Nenhuma mensagem de erro foi exibida' se foi silencioso",
      "screenshot_index": 5
    }}
  ]
}}

GUIA DE SEVERITY:
- critical: sistema crasha, dados corrompidos, XSS executado, SQL exposto, rotas não protegidas acessíveis, tela branca/500
- high: funcionalidade core quebrada, campo aceita dado completamente inválido sem erro, perda de dados confirmada
- medium: mensagem de erro incorreta, comportamento inesperado mas recuperável, feedback ausente em ação importante
- low: visual levemente quebrado, texto errado ou confuso, edge case muito improvável

GUIA DE CATEGORY:
- crash: sistema parou de funcionar, erro 500, tela branca, exceção não tratada
- security: XSS executado, SQL injection aceito, exposição de dados internos, rota restrita acessível sem autenticação
- validation: campo aceita valor inválido quando deveria rejeitar, ou rejeita valor válido incorretamente
- ui_error: layout quebrado, modal travado, loading infinito, elementos sobrepostos, componente não renderiza
- http_error: erros 4xx/5xx expostos ao usuário de forma não tratada
- functional: funcionalidade não funciona como esperado (ação não executa, dado não salva, fluxo não completa)
- ux: feedback ausente, ação silenciosa, mensagem confusa, estado inconsistente que não bloqueia mas confunde

Se não encontrar NENHUM bug real, retorne:
{{
  "summary": "Nenhum bug encontrado. A interface se comportou corretamente em todos os cenários de stress test executados.",
  "total_findings": 0,
  "findings": []
}}

PROIBIDO:
- NÃO use write_file ou escreva arquivos
- NÃO retorne texto fora do JSON
- NÃO invente bugs que não ocorreram
- NÃO documente comportamentos corretos como bugs
- NÃO repita o JSON
""".strip()

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
        
        # Helpers pra evitar "None" no prompt
        def s(value: Optional[Any], fallback: str = "") -> str:
            if value is None:
                return fallback
            v = str(value).strip()
            return v if v else fallback

        analysis_id = s(analysis.get("id"), "N/A")
        name = s(analysis.get("name"), "Sem nome")
        target_url = s(analysis.get("target_url"), "")

        credentials_block = AiUtils.build_credentials_block(
            analysis.get("access_credentials") or [],
            target_url=target_url,
        )
        description = s(analysis.get("description"), "")
        screen_context = s(analysis.get("screen_context"), "")
        playwright_description = s(analysis.get("playwright_description"), "")
        tests_description = s(analysis.get("tests_description"), "")
        documentation_description = s(analysis.get("documentation_description"), "")
        uiux_description = s(analysis.get("uiux_description"), "")

        # Regra especial: se não tiver target_url, não faz sentido gerar script
        if not target_url:
            raise ValueError("analysis.target_url é obrigatório para gerar script Playwright")

        objective_block_pw = f"""
    ==================================================
    ESCOPO RESTRITO — LEIA ANTES DE QUALQUER COISA
    ==================================================

    O QA definiu um objetivo específico para esta análise:
    "{description}"

    REGRA ABSOLUTA DE ESCOPO:
    - Automatize SOMENTE o que está descrito no objetivo acima.
    - Se o objetivo citar uma aba, funcionalidade, fluxo ou elemento específico,
      ignore completamente todos os outros elementos da interface.
    - Esta restrição tem PRIORIDADE MÁXIMA sobre qualquer outra instrução deste prompt.
    - NÃO amplie o escopo, mesmo que a interface tenha outras funcionalidades.
""" if description else ""

        prompt = f"""
    Você é um Engenheiro de QA Automation Sênior especialista em Playwright.

    Você deve gerar um script Playwright COMPLETO e EXECUTÁVEL para automatizar testes E2E
    da tela descrita abaixo, seguindo fielmente o contexto fornecido.
    {objective_block_pw}
    ==================================================
    DADOS DA ANÁLISE
    ==================================================

    analysis_id: {analysis_id}
    name: {name}
    target_url: {target_url}

    Credenciais de acesso:
    {credentials_block}

    Objetivo definido pelo QA:
    "{description or "Não informado — cubra os fluxos principais da interface."}"

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
    2) Execute SOMENTE os fluxos cobertos pelo objetivo do QA acima
    3) Valide listagem, filtros e paginação APENAS se estiverem no escopo do objetivo
    4) Valide criação e edição/atualização APENAS se estiverem no escopo do objetivo
    5) Cubra validações de campos obrigatórios e entradas inválidas dentro do escopo
    6) Gere asserts realistas e estáveis
    7) NÃO teste funcionalidades fora do escopo definido pelo QA

    ==================================================
    REGRAS IMPORTANTES (OBRIGATÓRIO)
    ==================================================

    - Gere testes com Playwright Test Runner (@playwright/test)
    - Use TypeScript por padrão
    - Use seletores estáveis baseados no que foi observado:
      - getByRole() com o nome/label EXATO do elemento
      - getByLabel() com o label EXATO do campo
      - getByPlaceholder() com o placeholder EXATO
      - getByText() com o texto EXATO visível
      - locator('#id') apenas se o id foi mencionado na descrição
    - NUNCA invente seletores para elementos não descritos
    - NUNCA use seletores frágeis (nth-child, classes dinâmicas, XPath genérico)
    - Inclua waits inteligentes:
      - aguarde navegação e carregamento com waitForLoadState ou expect().toBeVisible()
      - evite waitForTimeout fixo a menos que seja inevitável
    - Separe testes em blocos test.describe por seção/funcionalidade da tela
    - Use beforeEach para login/navegação quando aplicável
    - Se um elemento não existe na descrição, NÃO crie interação com ele
    - Se houver modais: valide abertura E fechamento
    - Se houver formulários: teste preenchimento válido, inválido e campos obrigatórios vazios
    - Se houver paginação ou filtros: teste somente os que foram descritos explicitamente

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


    def build_docs_prompt(analysis: Dict[str, Any]) -> str:
        """
        Monta um prompt para gerar documentação funcional
        estruturada em Markdown, pronta para exportação
        para Word / Pages / Google Docs.
        """

        def s(value: Optional[Any], fallback: str = "") -> str:
            if value is None:
                return fallback
            v = str(value).strip()
            return v if v else fallback

        name = s(analysis.get("name"), "Sem nome")
        target_url = s(analysis.get("target_url"), "N/A")
        description = s(analysis.get("description"), "")
        screen_context = s(analysis.get("screen_context"), "")
        documentation_description = s(analysis.get("documentation_description"), "")

        prompt = f"""
    Você é um **Analista de Sistemas Sênior / QA Funcional** especializado em
    documentação funcional de sistemas web.

    Seu objetivo é gerar uma **DOCUMENTAÇÃO FUNCIONAL PRECISA, COMPLETA E BEM ESTRUTURADA**
    para a tela descrita abaixo.

    REGRA ABSOLUTA: Documente SOMENTE o que está descrito nas informações fornecidas.
    NUNCA invente seções, funcionalidades, fluxos ou elementos que não apareçam na descrição.
    Se a informação não estiver na descrição, NÃO escreva sobre ela.

    Essa documentação será **exportada para Word / Pages / Google Docs**, portanto:

    - Utilize **Markdown simples e semântico**
    - Use `#` apenas para o título principal do documento
    - Use `##` para seções principais
    - Use `###` para subseções (use os nomes REAIS da interface, não nomes genéricos)
    - Use listas simples com `-`
    - NÃO use emojis
    - NÃO use HTML
    - NÃO use tabelas complexas
    - NÃO use formatação decorativa excessiva
    - Clareza e precisão são prioridade absoluta

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    CONTEXTO DA ANÁLISE
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    - Nome da tela / feature: {name}
    - URL da tela: {target_url}

    Descrição geral fornecida pelo QA:
    {description}

    Contexto de negócio:
    {screen_context}

    DESCRIÇÃO DETALHADA DA TELA (sua fonte primária — use 100% do que está aqui):
    {documentation_description}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    REGRAS DE GERAÇÃO
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    - Não invente regras de negócio.
    - Não faça suposições fora do que foi descrito.
    - Não escreva código.
    - Não cite ferramentas de teste.
    - Os nomes de seções e elementos devem refletir os NOMES REAIS observados na tela.
      Exemplo: se a seção se chama "Como funciona", use "Como funciona" — não "Funcionalidades".
    - Se a tela for uma landing page, documente cada seção da landing page pelo título real.
    - Se a tela for um formulário, documente cada campo pelo label real.
    - Se a tela for um dashboard, documente cada widget/card pelo nome real.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ESTRUTURA OBRIGATÓRIA
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # Documentação Funcional – {name}

    ## 1. Visão Geral
    - Objetivo principal da tela
    - Público-alvo
    - URL de acesso

    ## 2. Estrutura da Tela
    Liste todas as seções da tela na ordem em que aparecem.
    Use o título EXATO de cada seção conforme aparece na interface.

    ### [Título exato da seção 1]
    - O que esta seção contém
    - Propósito para o usuário

    ### [Título exato da seção 2]
    - O que esta seção contém
    - Propósito para o usuário

    (repita para todas as seções observadas)

    ## 3. Elementos Interativos
    Liste todos os elementos com os quais o usuário pode interagir.
    Use os labels/textos REAIS dos elementos.

    ### [Nome/label real do elemento]
    - Tipo (botão, campo, link, menu, etc.)
    - Finalidade
    - Comportamento ao interagir
    - Restrições ou validações observadas

    ## 4. Fluxos de Uso

    ### Fluxo Principal
    Descreva passo a passo o fluxo principal do usuário nesta tela.
    Base-se SOMENTE nos elementos e ações observados.

    ### Fluxos Alternativos
    Descreva variações do fluxo principal, se existirem.
    Omita esta subseção se não houver fluxos alternativos observados.

    ### Cenários de Erro ou Validação
    Descreva os comportamentos em entradas inválidas ou erros, se observados.
    Omita esta subseção se não houver erros/validações observados.

    ## 5. Regras de Negócio
    Liste apenas regras EXPLICITAMENTE observadas ou mencionadas no contexto.
    Se nenhuma regra explícita foi observada, escreva: "Nenhuma regra de negócio explícita identificada na interface."

    ## 6. Mensagens e Feedback
    Liste as mensagens reais exibidas na interface (sucesso, erro, validação, aviso).
    Se nenhuma mensagem foi observada, escreva: "Nenhuma mensagem de feedback observada durante a análise."

    ## 7. Observações
    - Pontos de atenção identificados
    - Limitações observadas na interface
    - Ambiguidades ou lacunas de informação

    Gere a documentação agora.
    """

        return prompt.strip()
