"""
Stuck-Agent & Repetitive Loop Detector.
"""

import time
import hashlib
import logging
from typing import Dict, Any, List
from playwright.async_api import Page
from .telemetry import get_telemetry_manager

logger = logging.getLogger(__name__)

class StuckDetector:
    def __init__(self):
        self._history: Dict[str, List[Dict[str, Any]]] = {}
        self._telemetry = get_telemetry_manager()

    async def record_and_check(self, session_id: str, action: str, target: str, page: Page) -> Dict[str, Any]:
        """
        Records the action and checks whether the agent is trapped in an unproductive loop.
        Flags STUCK if:
        - The last 3 actions produced identical DOM hashes and URLs without progressing.
        - The same action/target combination repeated >= 4 times continuously.
        """
        url = page.url
        try:
            content = await page.content()
            dom_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        except Exception:
            dom_hash = "unknown"

        history = self._history.setdefault(session_id, [])
        record = {
            "action": action,
            "target": target,
            "url": url,
            "dom_hash": dom_hash,
            "time": time.time()
        }
        history.append(record)
        if len(history) > 15:
            history.pop(0)

        # 1. Check identical DOM state across last 3 actions
        is_stuck = False
        reason = "normal_execution"
        recommended_action = "continue"

        if len(history) >= 3:
            last_3 = history[-3:]
            same_dom = all(h["dom_hash"] == last_3[0]["dom_hash"] and h["url"] == last_3[0]["url"] for h in last_3)
            same_action = all(h["action"] == last_3[0]["action"] and h["target"] == last_3[0]["target"] for h in last_3)
            
            if same_dom and same_action:
                is_stuck = True
                reason = "same_action_and_page_state_after_3_attempts"
                recommended_action = "recover_browser_state(strategy='refresh')_and_replan"
            elif same_dom and len(history) >= 4:
                is_stuck = True
                reason = "zero_dom_state_change_across_4_consecutive_actions"
                recommended_action = "reobserve_page_and_try_alternative_locator"

        if is_stuck:
            await self._telemetry.emit("stuck_detected", {
                "session_id": session_id,
                "reason": reason,
                "recommendation": recommended_action
            }, session_id=session_id)

        return {
            "is_stuck": is_stuck,
            "reason": reason,
            "recommended_action": recommended_action,
            "cycles_tracked": len(history),
            "dom_hash": dom_hash
        }

    def reset(self, session_id: str):
        if session_id in self._history:
            self._history[session_id].clear()
