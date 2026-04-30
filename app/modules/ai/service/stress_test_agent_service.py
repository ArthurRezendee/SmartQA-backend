import asyncio
import base64
import logging
import os
import time
from browser_use import Agent, Browser
from browser_use.llm import ChatOpenAI
from app.modules.ai.utils.ai_utils import AiUtils

logger = logging.getLogger(__name__)

_BROWSER_EXECUTABLE = os.getenv("BROWSER_EXECUTABLE_PATH", "/root/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome")
_STRESS_TEST_MODEL = os.getenv("STRESS_TEST_MODEL", "gpt-4.1")
_RETRY_DELAY_SECONDS = 5
_MAX_ATTEMPTS = 3

_CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-setuid-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
]


class StressTestAgentService:

    def run_stress_test(self, *, analysis: dict, stress_test_id: int) -> dict:
        credentials_block = AiUtils.build_credentials_block(
            analysis.get("access_credentials") or [],
            target_url=analysis.get("target_url", ""),
        )

        task = AiUtils.build_stress_test_prompt(
            analysis=analysis,
            credentials_block=credentials_block,
        )

        llm = ChatOpenAI(model=_STRESS_TEST_MODEL)

        screenshot_dir = f"/dados/stress_tests/{stress_test_id}"
        os.makedirs(screenshot_dir, exist_ok=True)

        def _run_agent() -> tuple[str, list]:
            browser = Browser(
                headless=True,
                executable_path=_BROWSER_EXECUTABLE,
                args=_CHROMIUM_ARGS,
                minimum_wait_page_load_time=2.0,
                wait_for_network_idle_page_load_time=3.0,
            )
            try:
                agent = Agent(
                    task=task,
                    browser=browser,
                    llm=llm,
                    vision_detail_level="low",
                    max_history_items=12,
                    llm_screenshot_size=(1280, 800),
                    use_thinking=False,
                )
                history = asyncio.run(agent.run(max_steps=200))
                result = (history.final_result() or "").strip()

                saved_paths = _save_screenshots(history, screenshot_dir, stress_test_id)
            finally:
                try:
                    asyncio.run(browser.close())
                except Exception:
                    pass

            if not result:
                raise ValueError("Stress test agent retornou resultado vazio")

            return result, saved_paths

        last_error = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                result, saved_paths = _run_agent()

                try:
                    data = AiUtils.parse_browseruse_json(result)
                except Exception as e:
                    raise ValueError(f"JSON inválido retornado pelo stress test agent: {e} | result={result[:500]}")

                if _page_never_loaded(data):
                    raise ValueError("Página não carregou — nenhum elemento foi testado. Retentando com nova sessão de browser.")

                findings = data.get("findings") or []
                for finding in findings:
                    idx = finding.get("screenshot_index")
                    if isinstance(idx, int) and 0 <= idx < len(saved_paths):
                        finding["screenshot_path"] = saved_paths[idx]
                    else:
                        finding["screenshot_path"] = None

                data["findings"] = findings
                return data

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[StressTest] Tentativa {attempt}/{_MAX_ATTEMPTS} falhou: {e}"
                    + (f" — aguardando {_RETRY_DELAY_SECONDS}s" if attempt < _MAX_ATTEMPTS else "")
                )
                if attempt < _MAX_ATTEMPTS:
                    time.sleep(_RETRY_DELAY_SECONDS)

        raise ValueError(f"Stress test falhou após {_MAX_ATTEMPTS} tentativas: {last_error}")


def _page_never_loaded(data: dict) -> bool:
    """Retorna True quando o agente encerrou sem conseguir testar nada — página nunca carregou."""
    findings = data.get("findings") or []
    if len(findings) != 1:
        return False
    f = findings[0]
    return (
        f.get("category") == "crash"
        and f.get("severity") == "critical"
        and "não carrega" in (f.get("title") or "").lower()
    )


def _save_screenshots(history, screenshot_dir: str, stress_test_id: int) -> list:
    saved_paths = []
    try:
        screenshots_b64 = history.screenshots(return_none_if_not_screenshot=False) or []
        for i, shot_b64 in enumerate(screenshots_b64):
            if not shot_b64:
                saved_paths.append(None)
                continue
            path = f"{screenshot_dir}/screenshot_{i}.png"
            try:
                with open(path, "wb") as f:
                    f.write(base64.b64decode(shot_b64))
                saved_paths.append(f"/dados/stress_tests/{stress_test_id}/screenshot_{i}.png")
            except Exception as e:
                logger.warning(f"[StressTest] Falha ao salvar screenshot {i}: {e}")
                saved_paths.append(None)
    except Exception as e:
        logger.warning(f"[StressTest] Falha ao acessar screenshots do histórico: {e}")
    return saved_paths
