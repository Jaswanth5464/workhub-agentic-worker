"""
Atomic Semantic Interaction Tools for Autonomous Browser Execution.
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page
from .element_resolver import ElementResolver
from .telemetry import get_telemetry_manager

logger = logging.getLogger(__name__)

class InteractionTools:
    def __init__(self):
        self._telemetry = get_telemetry_manager()

    async def click(self, target: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Clicks an element identified by semantic name, label, or selector."""
        loc, res_info = await ElementResolver.resolve(target, page)
        if not loc:
            await self._telemetry.emit("element_not_found", {"target": target}, session_id=session_id)
            return {"success": False, "error": f"Element '{target}' not found."}

        try:
            await loc.click(timeout=8000)
        except Exception:
            await loc.click(timeout=2000, force=True)

        await self._telemetry.emit("button_clicked", {"target": target, "resolver": res_info}, session_id=session_id)
        return {
            "success": True,
            "action": "click",
            "target": target,
            "resolved_by": res_info.get("resolved_by")
        }

    async def double_click(self, target: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Double clicks an element."""
        loc, res_info = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Element '{target}' not found."}

        await loc.dblclick(timeout=8000)
        return {"success": True, "action": "double_click", "target": target}

    async def fill_input(self, target: str, value: Any, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Fills an input, textarea, or form field."""
        loc, res_info = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Input field '{target}' not found."}

        try:
            await loc.fill(str(value), timeout=8000)
        except Exception:
            await loc.focus(timeout=2000)
            await page.keyboard.type(str(value), delay=25)

        await self._telemetry.emit("input_filled", {"target": target, "value": str(value)}, session_id=session_id)
        return {
            "success": True,
            "action": "fill_input",
            "target": target,
            "value": str(value),
            "resolved_by": res_info.get("resolved_by")
        }

    async def clear_input(self, target: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Clears an input field."""
        loc, _ = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Input field '{target}' not found."}

        await loc.fill("", timeout=5000)
        return {"success": True, "action": "clear_input", "target": target}

    async def select_option(self, target: str, value: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Selects an option from a dropdown / select element."""
        loc, res_info = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Dropdown '{target}' not found."}

        try:
            await loc.select_option(label=str(value), timeout=8000)
        except Exception:
            await loc.select_option(value=str(value), timeout=4000)

        return {
            "success": True,
            "action": "select_option",
            "target": target,
            "selected_value": value,
            "resolved_by": res_info.get("resolved_by")
        }

    async def check_checkbox(self, target: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Checks a checkbox or toggle."""
        loc, _ = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Checkbox '{target}' not found."}

        await loc.check(timeout=5000)
        return {"success": True, "action": "check_checkbox", "target": target}

    async def uncheck_checkbox(self, target: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Unchecks a checkbox or toggle."""
        loc, _ = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Checkbox '{target}' not found."}

        await loc.uncheck(timeout=5000)
        return {"success": True, "action": "uncheck_checkbox", "target": target}

    async def hover(self, target: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Hovers over an element."""
        loc, _ = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Element '{target}' not found."}

        await loc.hover(timeout=5000)
        return {"success": True, "action": "hover", "target": target}

    async def press_key(self, key: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Presses a keyboard key (e.g. 'Enter', 'Escape', 'Tab', 'ArrowDown')."""
        await page.keyboard.press(key)
        return {"success": True, "action": "press_key", "key": key}

    async def scroll(self, direction: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Scrolls the viewport up or down."""
        if direction.lower() in ["down", "bottom"]:
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
        else:
            await page.evaluate("window.scrollBy(0, -window.innerHeight)")
        return {"success": True, "action": "scroll", "direction": direction}

    async def upload_file(self, target: str, file_path: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Uploads a file to an input[type='file'] or upload dropzone."""
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return {"success": False, "error": f"File not found on disk: {file_path}"}

        loc, _ = await ElementResolver.resolve(target, page)
        if not loc:
            # Fallback to any file input on page
            loc = page.locator("input[type='file']").first

        if await loc.count() == 0:
            return {"success": False, "error": f"File input element not found for '{target}'."}

        await loc.set_input_files(abs_path)
        return {
            "success": True,
            "action": "upload_file",
            "file": abs_path,
            "filename": os.path.basename(abs_path)
        }
