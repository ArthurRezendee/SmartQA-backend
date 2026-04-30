import asyncio
import base64
import logging
import os

from browser_use import Agent, Browser
from browser_use.llm import ChatOpenAI

from app.modules.ai.utils.ai_utils import AiUtils

logger = logging.getLogger(__name__)

_BROWSER_EXECUTABLE = os.getenv("BROWSER_EXECUTABLE_PATH", "/root/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome")
_STRESS_TEST_MODEL = os.getenv("STRESS_TEST_MODEL", "gpt-4.1")

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

_MAX_ATTEMPTS = 2

# JS snippet that patches fetch/XHR to capture HTTP errors into window.__smartqa_errors
_NETWORK_MONITOR_JS = """
(function() {
    if (window.__smartqa_monitor) return;
    window.__smartqa_monitor = true;
    window.__smartqa_errors = window.__smartqa_errors || [];

    const orig_fetch = window.fetch;
    window.fetch = async function(...args) {
        const r = await orig_fetch(...args);
        if (r.status >= 400) {
            const url = (typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '').slice(-100);
            window.__smartqa_errors.push({method: 'FETCH', url, status: r.status});
        }
        return r;
    };

    const _open = XMLHttpRequest.prototype.open;
    const _send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {
        this.__smartqa_method = method;
        this.__smartqa_url = String(url).slice(-100);
        return _open.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function() {
        this.addEventListener('load', () => {
            if (this.status >= 400) {
                window.__smartqa_errors.push({
                    method: this.__smartqa_method || 'XHR',
                    url: this.__smartqa_url || '',
                    status: this.status
                });
            }
        });
        return _send.apply(this, arguments);
    };
})();
"""


class StressTestWorkerService:

    def run_worker(
        self,
        *,
        analysis: dict,
        worker_id: int,
        batch: list[dict],
        stress_test_id: int,
    ) -> dict:
        credentials_block = AiUtils.build_credentials_block(
            analysis.get("access_credentials") or [],
            target_url=analysis.get("target_url", ""),
        )
        task = AiUtils.build_worker_prompt(
            target_url=analysis.get("target_url", ""),
            credentials_block=credentials_block,
            worker_id=worker_id,
            batch=batch,
        )

        max_steps = AiUtils.calculate_max_steps(batch)
        logger.info(f"[Worker {worker_id}] max_steps={max_steps}, batch_size={len(batch)}")

        screenshot_dir = f"/dados/stress_tests/{stress_test_id}/worker_{worker_id}"
        os.makedirs(screenshot_dir, exist_ok=True)

        llm = ChatOpenAI(model=_STRESS_TEST_MODEL)

        last_error = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            browser = Browser(
                headless=True,
                executable_path=_BROWSER_EXECUTABLE,
                args=_CHROMIUM_ARGS,
                minimum_wait_page_load_time=2.0,
                wait_for_network_idle_page_load_time=3.0,
            )
            try:
                http_errors: list[dict] = []
                monitored_page_ids: set[int] = set()

                async def step_callback(state, output, step_number):
                    # Attach network listener + inject visible error banner on each step
                    try:
                        page = await browser.get_current_page()
                        pid = id(page)

                        # Attach Playwright response listener once per page object
                        if pid not in monitored_page_ids:
                            monitored_page_ids.add(pid)

                            def _on_response(response):
                                if response.status >= 400:
                                    http_errors.append({
                                        "method": response.request.method,
                                        "url": response.url[-100:],
                                        "status": response.status,
                                    })

                            page.on("response", _on_response)

                        # Inject JS monitor (idempotent — no-op if already injected)
                        await page.evaluate(_NETWORK_MONITOR_JS)

                        # Collect JS-captured errors too
                        js_errors = await page.evaluate("window.__smartqa_errors || []")
                        for e in js_errors:
                            if e not in http_errors:
                                http_errors.append(e)

                        # Render visible banner so the agent sees it in the next screenshot
                        if http_errors:
                            recent = http_errors[-3:]
                            parts = " | ".join(
                                f"{e.get('method','HTTP')} …{e.get('url','')} → {e.get('status','?')}"
                                for e in recent
                            )
                            escaped = parts.replace("\\", "\\\\").replace("'", "\\'")
                            await page.evaluate(f"""
                                (function() {{
                                    let el = document.getElementById('__smartqa_err');
                                    if (!el) {{
                                        el = document.createElement('div');
                                        el.id = '__smartqa_err';
                                        el.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;' +
                                            'background:#b71c1c;color:#fff;padding:6px 10px;' +
                                            'font:bold 12px monospace;word-break:break-all;';
                                        if (document.body) document.body.appendChild(el);
                                    }}
                                    el.textContent = 'ERROS HTTP: {escaped}';
                                }})();
                            """)
                    except Exception:
                        pass

                agent = Agent(
                    task=task,
                    browser=browser,
                    llm=llm,
                    vision_detail_level="low",
                    max_history_items=12,
                    llm_screenshot_size=(1280, 800),
                    use_thinking=False,
                    use_judge=False,
                    max_failures=5,
                    register_new_step_callback=step_callback,
                )
                history = asyncio.run(agent.run(max_steps=max_steps))
                result = (history.final_result() or "").strip()
                saved_paths = _save_screenshots(history, screenshot_dir, stress_test_id, worker_id)
            finally:
                try:
                    asyncio.run(browser.close())
                except Exception:
                    pass

            if not result:
                last_error = ValueError(f"Worker {worker_id} retornou resultado vazio")
                logger.warning(f"[Worker {worker_id}] Tentativa {attempt}/{_MAX_ATTEMPTS}: resultado vazio")
                continue

            try:
                data = AiUtils.parse_browseruse_json(result)
            except Exception as e:
                last_error = ValueError(f"JSON inválido do worker {worker_id}: {e} | result={result[:300]}")
                logger.warning(f"[Worker {worker_id}] Tentativa {attempt}/{_MAX_ATTEMPTS}: {last_error}")
                continue

            findings = data.get("findings") or []
            for finding in findings:
                idx = finding.get("screenshot_index")
                if isinstance(idx, int) and 0 <= idx < len(saved_paths):
                    finding["screenshot_path"] = saved_paths[idx]
                else:
                    finding["screenshot_path"] = None

            attacks_log = data.get("attacks_log") or []

            if http_errors:
                logger.info(
                    f"[Worker {worker_id}] {len(http_errors)} erros HTTP capturados: "
                    + ", ".join(f"{e.get('status')} {e.get('url','')[-40:]}" for e in http_errors[:5])
                )

            logger.info(
                f"[Worker {worker_id}] Concluído: {len(findings)} findings, "
                f"{len(attacks_log)} steps no attacks_log"
            )
            return {
                "worker_id": worker_id,
                "findings": findings,
                "attacks_log": attacks_log,
                "http_errors": http_errors,
            }

        raise ValueError(f"Worker {worker_id} falhou após {_MAX_ATTEMPTS} tentativas: {last_error}")


def _save_screenshots(history, screenshot_dir: str, stress_test_id: int, worker_id: int) -> list:
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
                saved_paths.append(f"/dados/stress_tests/{stress_test_id}/worker_{worker_id}/screenshot_{i}.png")
            except Exception as e:
                logger.warning(f"[Worker {worker_id}] Falha ao salvar screenshot {i}: {e}")
                saved_paths.append(None)
    except Exception as e:
        logger.warning(f"[Worker {worker_id}] Falha ao acessar screenshots: {e}")
    return saved_paths
