import os
import json
import logging
from typing import Any, Dict, List

from openai import OpenAI

logger = logging.getLogger("uvicorn.error")


class TestCaseAgentError(Exception):
    """Erro genérico do agente de casos de teste."""


class TestCaseAgentParseError(TestCaseAgentError):
    """Erro ao parsear JSON retornado pelo modelo."""


class TestCaseAgent:
    def __init__(self, model: str = "gpt-4.1-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não definida no ambiente")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _validate(self, data: Any) -> List[Dict[str, Any]]:
        if not isinstance(data, list) or not data:
            raise TestCaseAgentParseError("Retorno não é uma lista de casos de teste")

        required_case_keys = {
            "title",
            "description",
            "objective",
            "test_type",
            "scenario_type",
            "priority",
            "risk_level",
            "preconditions",
            "expected_result",
            "steps",
        }

        required_step_keys = {"order", "action", "expected_result"}

        for i, tc in enumerate(data, start=1):
            if not isinstance(tc, dict):
                raise TestCaseAgentParseError(f"Caso #{i} não é um objeto")

            missing = required_case_keys - set(tc.keys())
            if missing:
                raise TestCaseAgentParseError(f"Caso #{i} faltando campos: {sorted(missing)}")

            if not isinstance(tc["steps"], list) or not tc["steps"]:
                raise TestCaseAgentParseError(f"Caso #{i} veio sem steps")

            for j, step in enumerate(tc["steps"], start=1):
                if not isinstance(step, dict):
                    raise TestCaseAgentParseError(f"Caso #{i} step #{j} não é objeto")

                missing_step = required_step_keys - set(step.keys())
                if missing_step:
                    raise TestCaseAgentParseError(
                        f"Caso #{i} step #{j} faltando campos: {sorted(missing_step)}"
                    )

            # ordena steps
            tc["steps"] = sorted(tc["steps"], key=lambda s: int(s.get("order", 0)))

        return data

    def generate(self, full_prompt: str) -> List[Dict[str, Any]]:
        if not full_prompt or not full_prompt.strip():
            raise TestCaseAgentError("full_prompt está vazio")

        system_prompt = (
            "Você é um QA Sênior altamente experiente, especializado em testes "
            "funcionais, regressão e prevenção de bugs críticos em sistemas web.\n"
            "RETORNE APENAS JSON válido.\n"
            "NUNCA retorne markdown.\n"
            "NUNCA retorne texto fora do JSON.\n"
            "O JSON deve ser um ARRAY na raiz: [ {...}, {...} ]"
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
                response_format={"type": "json_object"},
            )

            content = (response.choices[0].message.content or "").strip()
            if not content:
                raise TestCaseAgentParseError("Modelo retornou resposta vazia")

           
            try:
                obj = json.loads(content)
            except Exception as e:
                logger.error("[IA][TEST_CASE_AGENT] JSON inválido retornado:\n%s", content[:2000])
                raise TestCaseAgentParseError(f"Falha ao json.loads: {e}") from e

            
            items = None
            if isinstance(obj, dict):
                if isinstance(obj.get("items"), list):
                    items = obj["items"]
                elif isinstance(obj.get("test_cases"), list):
                    items = obj["test_cases"]
                elif isinstance(obj.get("data"), list):
                    items = obj["data"]

            if items is None:
                raise TestCaseAgentParseError(
                    "Modelo não retornou no formato esperado. Esperado: {'items': [ ... ]}"
                )

            return self._validate(items)

        except TestCaseAgentParseError:
            logger.exception("[IA][TEST_CASE_AGENT] Erro ao parsear JSON do modelo")
            raise
        except Exception as e:
            logger.exception("[IA][TEST_CASE_AGENT] Falha ao gerar casos de teste")
            raise TestCaseAgentError(f"Falha ao gerar casos de teste: {e}") from e
