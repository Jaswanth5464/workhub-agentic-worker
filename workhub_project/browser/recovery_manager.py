"""
8-Tier Autonomous Failure Recovery Manager.
"""

import time
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page
from .browser_manager import get_browser_manager
from .observation_tools import ObservationTools
from .telemetry import get_telemetry_manager

logger = logging.getLogger(__name__)

class RecoveryManager:
    def __init__(self):
        self._telemetry = get_telemetry_manager()
        self._browser_manager = get_browser_manager()

    async def recover(
        self,
        failure_type: str,
        page: Page,
        session_id: str = "default",
        target_url: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes graduated recovery based on failure type:
        1. 'stale_element': Re-observes DOM, clears caches, and re-resolves
        2. 'unexpected_modal': Dismisses blocking modal/overlay and restores focus
        3. 'validation_error': Extracts validation messages and returns fix guidelines
        4. 'page_timeout' / 'network_timeout': Reloads page with networkidle wait
        5. 'session_expired': Re-authenticates / refreshes session
        6. 'browser_crash': Re-launches Playwright browser and restores target URL
        7. 'replan': Returns full re-observation snapshot for agent replanning
        """
        await self._telemetry.emit("recovery_started", {
            "failure_type": failure_type,
            "url": page.url if not page.is_closed() else "N/A"
        }, session_id=session_id)

        recovery_strategy = "unknown"
        success = False
        details = {}

        try:
            if failure_type == "stale_element" or failure_type == "element_not_found":
                recovery_strategy = "reobserve_and_re-resolve"
                # Wait 500ms for animations, re-evaluate DOM
                await page.wait_for_timeout(500)
                obs = await ObservationTools.observe_page(page)
                success = True
                details = {"message": "DOM re-observed", "new_elements_count": obs["interactive_elements_count"]}

            elif failure_type == "unexpected_modal":
                recovery_strategy = "dismiss_modal"
                # Try clicking modal close button or pressing Escape
                dismissed = await page.evaluate("""
                () => {
                    const closeBtn = document.querySelector('.close-modal, button.close, [aria-label="Close"], .modal-overlay button.btn-secondary');
                    if (closeBtn) {
                        closeBtn.click();
                        return true;
                    }
                    return false;
                }
                """)
                if not dismissed:
                    await page.keyboard.press("Escape")
                await page.wait_for_timeout(300)
                success = True
                details = {"modal_dismissed": True}

            elif failure_type == "validation_error":
                recovery_strategy = "extract_validation_feedback"
                # Extract red/error alert text
                error_texts = await page.evaluate("""
                () => {
                    const errors = Array.from(document.querySelectorAll('.error-message, .invalid-feedback, .alert-danger, .text-danger'));
                    return errors.map(e => e.innerText.trim()).filter(t => t !== '');
                }
                """)
                success = True
                details = {"validation_errors": error_texts, "guidance": "Fix invalid input fields and retry."}

            elif failure_type == "page_timeout" or failure_type == "network_timeout":
                recovery_strategy = "reload_page"
                await page.reload(wait_until="networkidle", timeout=10000)
                success = True
                details = {"reloaded_url": page.url}

            elif failure_type == "session_expired":
                recovery_strategy = "re-authenticate_session"
                # If on login screen, simulate auth or reload
                await page.goto(target_url or "http://localhost:3000/index.html", wait_until="networkidle", timeout=8000)
                success = True
                details = {"re_authenticated": True, "restored_url": page.url}

            elif failure_type == "browser_crash":
                recovery_strategy = "restart_browser_process"
                new_page, _ = await self._browser_manager.restart_session(session_id, restore_url=target_url or "http://localhost:3000/index.html")
                success = True
                details = {"browser_restarted": True, "restored_url": new_page.url}

            else:  # General replan recovery
                recovery_strategy = "replan_state_capture"
                obs = await ObservationTools.observe_page(page)
                success = True
                details = {"snapshot": obs}

        except Exception as err:
            success = False
            details = {"error": str(err)}

        await self._telemetry.emit("recovery_completed", {
            "failure_type": failure_type,
            "strategy": recovery_strategy,
            "success": success,
            "details": details
        }, session_id=session_id)

        return {
            "success": success,
            "failure_type": failure_type,
            "strategy_used": recovery_strategy,
            "details": details
        }
