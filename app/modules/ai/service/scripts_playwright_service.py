import os
import json
import logging
import re
import ast
from typing import Any, Dict

from openai import OpenAI

logger = logging.getLogger("uvicorn.error")


class ScriptsPlaywrightAgentError(Exception):
    """Erro genérico do agente de geração de scripts Playwright."""


class ScriptsPlaywrightParseError(ScriptsPlaywrightAgentError):
    """Erro ao parsear JSON retornado pelo modelo."""


class ScriptsPlaywrightValidationError(ScriptsPlaywrightAgentError):
    """Erro de validação do schema retornado."""


class ScriptsPlaywrightAgent:
    """
    Agente responsável por gerar scripts Playwright a partir de um prompt completo.
    Retorno obrigatório do modelo: JSON object com:
      {
        "language": "typescript|javascript",
        "framework": "playwright",
        "title": "string",
        "script": "string"
      }
    """

    def __init__(self, model: str = "gpt-4.1-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não definida no ambiente")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    # -----------------------------
    # Parsing robusto do JSON
    # -----------------------------
    def _parse_json_object(self, content: str) -> Dict[str, Any]:
        if not content or not content.strip():
            raise ScriptsPlaywrightParseError("Modelo retornou resposta vazia")

        raw = content.strip()

        # 1) tenta capturar primeiro objeto {...} (remove lixo tipo "Final Result:")
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if m:
            raw = m.group(0).strip()

        # 2) json.loads direto
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # 3) JSON escapado (ex: {\"a\":1})
        try:
            unescaped = raw.replace('\\"', '"')
            obj = json.loads(unescaped)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # 4) literal_eval fallback
        try:
            evaluated = ast.literal_eval(raw)
            if isinstance(evaluated, dict):
                return evaluated
            if isinstance(evaluated, str):
                obj = json.loads(evaluated)
                if isinstance(obj, dict):
                    return obj
        except Exception:
            pass

        logger.error("[IA][PLAYWRIGHT_AGENT] JSON inválido retornado:\n%s", content[:2500])
        raise ScriptsPlaywrightParseError("Não foi possível parsear JSON retornado pelo modelo")

    # -----------------------------
    # Validação do schema
    # -----------------------------
    def _validate(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ScriptsPlaywrightValidationError("Retorno não é um objeto JSON")

        required_keys = {"language", "framework", "title", "script"}
        missing = required_keys - set(data.keys())
        if missing:
            raise ScriptsPlaywrightValidationError(f"Faltando chaves obrigatórias: {sorted(missing)}")

        language = str(data.get("language") or "").strip().lower()
        framework = str(data.get("framework") or "").strip().lower()
        title = str(data.get("title") or "").strip()
        script = str(data.get("script") or "").strip()

        if framework != "playwright":
            raise ScriptsPlaywrightValidationError(f"framework inválido: {framework!r} (esperado 'playwright')")

        if language not in {"typescript", "javascript"}:
            raise ScriptsPlaywrightValidationError(
                f"language inválido: {language!r} (esperado 'typescript' ou 'javascript')"
            )

        if not title:
            raise ScriptsPlaywrightValidationError("title vazio")

        if not script:
            raise ScriptsPlaywrightValidationError("script vazio")

        # sanity checks úteis
        if "@playwright/test" not in script:
            raise ScriptsPlaywrightValidationError(
                "script parece inválido: não contém import de '@playwright/test'"
            )

        if "test(" not in script and "test.describe" not in script:
            raise ScriptsPlaywrightValidationError(
                "script parece inválido: não contém blocos de teste Playwright (test/describe)"
            )

        data["language"] = language
        data["framework"] = framework
        data["title"] = title
        data["script"] = script

        return data

    # -----------------------------
    # Geração
    # -----------------------------
    def generate(self, full_prompt: str) -> Dict[str, Any]:
        if not full_prompt or not full_prompt.strip():
            raise ScriptsPlaywrightAgentError("full_prompt está vazio")

        system_prompt = (
            "Você é um Engenheiro de QA Automation Sênior especialista em Playwright.\n"
            "RETORNE APENAS JSON válido.\n"
            "NUNCA retorne markdown.\n"
            "NUNCA retorne texto fora do JSON.\n"
            "A raiz do JSON deve ser um OBJETO.\n"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                top_p=0.9,
                max_tokens=20000,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt},
                ],
                # Força JSON object
                response_format={"type": "json_object"},
            )

            content = (response.choices[0].message.content or "").strip()
            obj = self._parse_json_object(content)
            return self._validate(obj)

        except (ScriptsPlaywrightParseError, ScriptsPlaywrightValidationError):
            logger.exception("[IA][PLAYWRIGHT_AGENT] Erro ao parsear/validar JSON do modelo")
            raise
        except Exception as e:
            logger.exception("[IA][PLAYWRIGHT_AGENT] Falha ao gerar script Playwright")
            raise ScriptsPlaywrightAgentError(f"Falha ao gerar script Playwright: {e}") from e
