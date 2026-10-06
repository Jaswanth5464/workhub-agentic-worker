"""
Playwright Browser Lifecycle and Session Manager.
"""

import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from .telemetry import get_telemetry_manager

logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._telemetry = get_telemetry_manager()

    async def get_session(self, session_id: str = "default") -> Tuple[Any, Any]:
        """Ensures a Playwright browser session exists and is alive for session_id."""
        if session_id not in self._sessions or self._sessions[session_id]["page"].is_closed():
            if not self._playwright:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()

            headless_mode = os.environ.get("HEADLESS", "false").lower() == "true"
            data_dir = Path(f"./browser_session_{session_id}")
            data_dir.mkdir(parents=True, exist_ok=True)

            context = None
            try:
                context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(data_dir),
                    headless=headless_mode,
                    slow_mo=200,
                    viewport=None,
                    args=[
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox"
                    ]
                )
            except Exception:
                browser = await self._playwright.chromium.launch(
                    headless=headless_mode,
                    slow_mo=200,
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                context = await browser.new_context(viewport=None)
            
            page = context.pages[0] if context.pages else await context.new_page()

            
            self._sessions[session_id] = {
                "context": context,
                "page": page,
                "created_at": time.time(),
                "last_active": time.time(),
                "last_dom_hash": "",
                "subgoal": "Initialization"
            }
            
            await self._telemetry.emit("browser_session_started", {
                "session_id": session_id,
                "headless": headless_mode
            }, session_id=session_id)

        self._sessions[session_id]["last_active"] = time.time()
        return self._sessions[session_id]["page"], self._sessions[session_id]["context"]

    async def close_session(self, session_id: str = "default"):
        """Closes browser session and cleans up resources."""
        if session_id in self._sessions:
            try:
                await self._sessions[session_id]["context"].close()
            except Exception:
                pass
            del self._sessions[session_id]
            await self._telemetry.emit("browser_session_closed", {"session_id": session_id}, session_id=session_id)

    async def restart_session(self, session_id: str = "default", restore_url: Optional[str] = None) -> Tuple[Any, Any]:
        """Restarts the browser session cleanly (used after crash or recovery)."""
        await self.close_session(session_id)
        page, context = await self.get_session(session_id)
        if restore_url:
            await page.goto(restore_url, wait_until="networkidle", timeout=10000)
        await self._telemetry.emit("browser_restarted", {"session_id": session_id, "restored_url": restore_url}, session_id=session_id)
        return page, context

    async def check_health(self, session_id: str = "default") -> Dict[str, Any]:
        """Returns diagnostic health metrics of the browser instance."""
        if session_id not in self._sessions:
            return {"status": "NOT_STARTED", "responsive": False}
            
        page = self._sessions[session_id]["page"]
        context = self._sessions[session_id]["context"]
        
        try:
            if page.is_closed():
                return {"status": "CLOSED", "responsive": False}
                
            title = await page.title()
            url = page.url
            ready_state = await page.evaluate("() => document.readyState")
            tabs_count = len(context.pages)
            
            return {
                "status": "HEALTHY",
                "url": url,
                "title": title,
                "ready_state": ready_state,
                "active_tabs": tabs_count,
                "responsive": True
            }
        except Exception as e:
            return {
                "status": "UNHEALTHY",
                "error": str(e),
                "responsive": False
            }

_manager_instance = BrowserManager()

def get_browser_manager() -> BrowserManager:
    return _manager_instance
