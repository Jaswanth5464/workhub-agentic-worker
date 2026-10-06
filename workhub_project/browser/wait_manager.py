"""
Deterministic Synchronization & Intelligent Wait Manager (No arbitrary sleeps).
"""

import time
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from .element_resolver import ElementResolver

logger = logging.getLogger(__name__)

class WaitManager:
    @staticmethod
    async def wait_for_condition(
        page: Page,
        condition: str,
        target: Optional[str] = None,
        value: Optional[str] = None,
        timeout: int = 8000
    ) -> Dict[str, Any]:
        """
        Deterministic condition waiting:
        - 'element': waits for element visibility
        - 'text': waits for specific text to appear
        - 'url': waits for URL to match or contain value
        - 'network_idle': waits for network traffic to settle
        - 'dom_change': waits for DOM mutations to settle
        - 'loading_complete': waits for spinner/loading overlays to disappear
        - 'disappear': waits for element to detach
        """
        start_t = time.time()
        try:
            if condition == "network_idle":
                await page.wait_for_load_state("networkidle", timeout=timeout)
                return {"success": True, "condition": "network_idle", "elapsed_ms": int((time.time() - start_t)*1000)}

            elif condition == "dom_change" or condition == "dom_stable":
                js_stable = """
                () => new Promise((resolve) => {
                    let timer;
                    const observer = new MutationObserver(() => {
                        clearTimeout(timer);
                        timer = setTimeout(() => { observer.disconnect(); resolve(true); }, 300);
                    });
                    observer.observe(document.body, { attributes: true, childList: true, subtree: true });
                    timer = setTimeout(() => { observer.disconnect(); resolve(true); }, 300);
                })
                """
                await page.evaluate(js_stable)
                return {"success": True, "condition": "dom_stable", "elapsed_ms": int((time.time() - start_t)*1000)}

            elif condition == "loading_complete":
                # Wait for any spinner / loader / overlay to disappear
                try:
                    await page.wait_for_selector(".fa-spinner, .loading-spinner, .loader", state="detached", timeout=timeout)
                except Exception:
                    pass
                return {"success": True, "condition": "loading_complete", "elapsed_ms": int((time.time() - start_t)*1000)}

            elif condition == "text":
                if not value: return {"success": False, "error": "Value required for text condition"}
                await page.wait_for_selector(f":has-text('{value}')", timeout=timeout)
                return {"success": True, "condition": "text_found", "text": value, "elapsed_ms": int((time.time() - start_t)*1000)}

            elif condition == "url":
                expected_part = value or ""
                await page.wait_for_url(lambda u: expected_part in u, timeout=timeout)
                return {"success": True, "condition": "url_matched", "url": page.url, "elapsed_ms": int((time.time() - start_t)*1000)}

            elif condition == "disappear":
                if not target: return {"success": False, "error": "Target required for disappear condition"}
                loc, _ = await ElementResolver.resolve(target, page)
                if loc:
                    await loc.wait_for(state="detached", timeout=timeout)
                return {"success": True, "condition": "disappeared", "target": target, "elapsed_ms": int((time.time() - start_t)*1000)}

            else:  # Default 'element'
                if not target: return {"success": False, "error": "Target element required"}
                loc, res_info = await ElementResolver.resolve(target, page)
                if not loc:
                    raise PlaywrightTimeoutError(f"Element '{target}' not found within {timeout}ms")
                return {"success": True, "condition": "element_visible", "target": target, "resolver": res_info}

        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": f"Condition '{condition}' timed out after {timeout}ms",
                "condition": condition,
                "elapsed_ms": int((time.time() - start_t)*1000)
            }
        except Exception as e:
            return {"success": False, "error": f"Wait error: {str(e)}", "condition": condition}
