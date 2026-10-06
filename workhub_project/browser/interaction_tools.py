"""
Atomic Semantic Interaction Tools for Autonomous Browser Execution.
"""

import os
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page
from .element_resolver import ElementResolver
from .telemetry import get_telemetry_manager

logger = logging.getLogger(__name__)

class InteractionTools:
    def __init__(self):
        self._telemetry = get_telemetry_manager()

    async def _show_visual_indicator(self, page: Page, loc, action_type: str, label_text: str = ""):
        """
        Renders a glowing visual indicator and floating action badge on the target element
        so observers can visibly see real-time physical AI browser interactions.
        """
        try:
            js = """
            ([element, actionType, labelText]) => {
                if (!element) return;
                
                // Remove previous indicators
                document.querySelectorAll('.ai-visual-indicator-badge, .ai-visual-indicator-ring').forEach(e => e.remove());
                
                const rect = element.getBoundingClientRect();
                const colors = {
                    'click': { border: '#00E5FF', bg: 'rgba(0, 229, 255, 0.25)', badge: '#00B4D8', text: '#FFFFFF', icon: '👆' },
                    'type': { border: '#FFD700', bg: 'rgba(255, 215, 0, 0.25)', badge: '#D97706', text: '#FFFFFF', icon: '✍️' },
                    'select': { border: '#10B981', bg: 'rgba(16, 185, 129, 0.25)', badge: '#059669', text: '#FFFFFF', icon: '🔽' },
                    'toggle': { border: '#8B5CF6', bg: 'rgba(139, 92, 246, 0.25)', badge: '#7C3AED', text: '#FFFFFF', icon: '☑️' },
                    'clear': { border: '#EF4444', bg: 'rgba(239, 68, 68, 0.25)', badge: '#DC2626', text: '#FFFFFF', icon: '🧹' }
                };
                const theme = colors[actionType] || colors['click'];
                
                // 1. Highlight Ring
                const ring = document.createElement('div');
                ring.className = 'ai-visual-indicator-ring';
                ring.style.cssText = `
                    position: fixed;
                    left: ${Math.max(0, rect.left - 4)}px;
                    top: ${Math.max(0, rect.top - 4)}px;
                    width: ${Math.max(20, rect.width + 8)}px;
                    height: ${Math.max(20, rect.height + 8)}px;
                    border: 3px solid ${theme.border};
                    background: ${theme.bg};
                    border-radius: 6px;
                    pointer-events: none;
                    z-index: 999999;
                    box-shadow: 0 0 18px ${theme.border};
                    transition: all 0.2s ease-out;
                    animation: aiPulse 0.5s infinite alternate;
                `;
                
                // 2. Action Badge
                const badge = document.createElement('div');
                badge.className = 'ai-visual-indicator-badge';
                badge.innerHTML = `<span>${theme.icon} <strong>AI ${actionType.toUpperCase()}</strong>: "${labelText || 'Target'}"</span>`;
                badge.style.cssText = `
                    position: fixed;
                    left: ${Math.max(10, rect.left)}px;
                    top: ${Math.max(10, rect.top - 32)}px;
                    background: ${theme.badge};
                    color: ${theme.text};
                    font-family: system-ui, -apple-system, sans-serif;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 4px 10px;
                    border-radius: 20px;
                    pointer-events: none;
                    z-index: 1000000;
                    box-shadow: 0 4px 14px rgba(0,0,0,0.35);
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    white-space: nowrap;
                    animation: aiSlideDown 0.2s ease-out;
                `;
                
                if (!document.getElementById('ai-indicator-styles')) {
                    const style = document.createElement('style');
                    style.id = 'ai-indicator-styles';
                    style.textContent = `
                        @keyframes aiPulse {
                            0% { transform: scale(1); opacity: 0.85; }
                            100% { transform: scale(1.03); opacity: 1; box-shadow: 0 0 24px rgba(0,229,255,0.9); }
                        }
                        @keyframes aiSlideDown {
                            from { transform: translateY(-6px); opacity: 0; }
                            to { transform: translateY(0); opacity: 1; }
                        }
                    `;
                    document.head.appendChild(style);
                }
                
                document.body.appendChild(ring);
                document.body.appendChild(badge);
            }
            """
            await loc.evaluate(js, [action_type, str(label_text)[:35]])
            await asyncio.sleep(0.3)
        except Exception:
            pass

    async def _hide_visual_indicator(self, page: Page):
        """Fades out and removes visual indicators."""
        try:
            await page.evaluate("""
                () => {
                    document.querySelectorAll('.ai-visual-indicator-badge, .ai-visual-indicator-ring').forEach(e => {
                        e.style.opacity = '0';
                        setTimeout(() => e.remove(), 200);
                    });
                }
            """)
            await asyncio.sleep(0.15)
        except Exception:
            pass

    async def click(self, target: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Clicks an element identified by semantic name, label, or selector."""
        loc, res_info = await ElementResolver.resolve(target, page)
        if not loc:
            await self._telemetry.emit("element_not_found", {"target": target}, session_id=session_id)
            return {"success": False, "error": f"Element '{target}' not found."}

        # Show visual cyan ring & action badge
        await self._show_visual_indicator(page, loc, action_type="click", label_text=target)

        try:
            await loc.click(timeout=8000)
        except Exception:
            await loc.click(timeout=2000, force=True)

        await self._hide_visual_indicator(page)
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

        await self._show_visual_indicator(page, loc, action_type="click", label_text=f"2x {target}")
        await loc.dblclick(timeout=8000)
        await self._hide_visual_indicator(page)
        return {"success": True, "action": "double_click", "target": target}

    async def fill_input(self, target: str, value: Any, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Fills an input, textarea, or form field with visible sequential keystrokes."""
        loc, res_info = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Input field '{target}' not found."}

        # Show visual amber gold ring & typing badge
        await self._show_visual_indicator(page, loc, action_type="type", label_text=f"{target} → '{value}'")

        try:
            await loc.fill("", timeout=4000)
            if hasattr(loc, "press_sequentially"):
                await loc.press_sequentially(str(value), delay=40)
            else:
                await loc.type(str(value), delay=40)
        except Exception:
            try:
                await loc.focus(timeout=2000)
                await page.keyboard.type(str(value), delay=40)
            except Exception:
                await loc.fill(str(value), timeout=4000)

        await self._hide_visual_indicator(page)
        await self._telemetry.emit("input_filled", {"target": target, "value": str(value)}, session_id=session_id)
        return {
            "success": True,
            "action": "fill_input",
            "target": target,
            "value": str(value),
            "resolved_by": res_info.get("resolved_by")
        }

    async def clear_input(self, target: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Clears an input field with visual highlight."""
        loc, _ = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Input field '{target}' not found."}

        await self._show_visual_indicator(page, loc, action_type="clear", label_text=f"Clear {target}")
        await loc.fill("", timeout=5000)
        await self._hide_visual_indicator(page)
        return {"success": True, "action": "clear_input", "target": target}

    async def select_option(self, target: str, value: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Selects an option from a dropdown / select element with resilient partial matching & emerald glow."""
        loc, res_info = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Dropdown '{target}' not found."}

        # Show visual emerald green ring & select badge
        await self._show_visual_indicator(page, loc, action_type="select", label_text=f"{target} → '{value}'")

        options_resolver_js = """
        ([selectEl, searchVal]) => {
            if (!selectEl || selectEl.tagName !== 'SELECT') return { success: false, error: 'Target is not a select element', options: [] };
            const lower = String(searchVal).toLowerCase().trim();
            const opts = Array.from(selectEl.options).map(o => ({
                value: o.value,
                text: (o.text || '').trim(),
                label: (o.label || '').trim()
            }));

            // Exact match
            let matched = opts.find(o => o.value.toLowerCase() === lower || o.text.toLowerCase() === lower || o.label.toLowerCase() === lower);
            // Partial match
            if (!matched) {
                matched = opts.find(o => o.text.toLowerCase().includes(lower) || o.value.toLowerCase().includes(lower) || o.label.toLowerCase().includes(lower));
            }
            // Token match
            if (!matched) {
                const tokens = lower.split(/\\s+/).filter(t => t.length > 2);
                if (tokens.length > 0) {
                    matched = opts.find(o => {
                        const fullStr = (o.text + " " + o.value + " " + o.label).toLowerCase();
                        return tokens.some(tok => fullStr.includes(tok));
                    });
                }
            }

            if (matched) {
                selectEl.value = matched.value;
                selectEl.dispatchEvent(new Event('change', { bubbles: true }));
                selectEl.dispatchEvent(new Event('input', { bubbles: true }));
                return { success: true, matched_value: matched.value, matched_text: matched.text };
            }

            return { success: false, options: opts.map(o => o.text || o.value).filter(Boolean) };
        }
        """

        try:
            res = await loc.evaluate(options_resolver_js, str(value).strip())
        except Exception as e:
            res = {"success": False, "error": str(e), "options": []}

        await self._hide_visual_indicator(page)

        if res.get("success"):
            return {
                "success": True,
                "action": "select_option",
                "target": target,
                "selected_value": res.get("matched_value"),
                "matched_label": res.get("matched_text"),
                "resolved_by": res_info.get("resolved_by")
            }
        else:
            avail = res.get("options", [])
            avail_preview = ", ".join([f"'{opt}'" for opt in avail[:8]])
            return {
                "success": False,
                "error": f"Option '{value}' not found in dropdown '{target}'. Available choices: [{avail_preview}]",
                "resolved_by": res_info.get("resolved_by")
            }

    async def check_checkbox(self, target: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Checks a checkbox or toggle with visual purple indicator."""
        loc, _ = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Checkbox '{target}' not found."}

        await self._show_visual_indicator(page, loc, action_type="toggle", label_text=f"Check {target}")
        await loc.check(timeout=5000)
        await self._hide_visual_indicator(page)
        return {"success": True, "action": "check_checkbox", "target": target}

    async def uncheck_checkbox(self, target: str, page: Page, session_id: str = "default") -> Dict[str, Any]:
        """Unchecks a checkbox or toggle with visual purple indicator."""
        loc, _ = await ElementResolver.resolve(target, page)
        if not loc:
            return {"success": False, "error": f"Checkbox '{target}' not found."}

        await self._show_visual_indicator(page, loc, action_type="toggle", label_text=f"Uncheck {target}")
        await loc.uncheck(timeout=5000)
        await self._hide_visual_indicator(page)
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

