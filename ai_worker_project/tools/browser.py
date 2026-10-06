"""
Agentic Browser Automation Tool.

Supports complex workflows, DOM observation, element verification, bounded retries, 
domain restrictions, and human-in-the-loop safeguards for critical actions.
"""

import json
import logging
import asyncio
import os
from urllib.parse import urlparse
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel

logger = logging.getLogger(__name__)

# Security & Safety
ALLOWED_DOMAINS = ["workhub.local", "localhost", "127.0.0.1", "example.com", "centralign.local"]
MAX_BROWSER_RETRIES = 3
ACTION_TIMEOUT = 10000

_sessions = {}

async def _ensure_started(run_id: str):
    global _playwright
    
    if run_id not in _sessions:
        if not _playwright:
            from playwright.async_api import async_playwright
            _playwright = await async_playwright().start()
            
        context = await _playwright.chromium.launch_persistent_context(
            user_data_dir=f"./browser_session_{run_id}",
            headless=False,
            slow_mo=500,
            args=["--start-maximized"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        _sessions[run_id] = {"context": context, "page": page}
        
    return _sessions[run_id]["page"], _sessions[run_id]["context"]

class BrowserTool(Tool):
    name = "browser"
    description = (
        "Controls a headless web browser for UI interaction. "
        "Actions: 'open_page', 'observe', 'click', 'type', 'select', 'extract_text', 'verify_state', 'screenshot', 'drag_and_drop', 'scroll_down', 'scroll_up', 'new_tab', 'switch_tab', 'close_tab'. "
        "CRITICAL TOOL SELECTION RULE: DO NOT use this tool for everything! If the user asks for HR data, use the direct HR API tools. If they ask for database info, use sql_query. ONLY use the browser when explicitly instructed to navigate to a website or visually verify a UI. "
        "When using: Always use 'observe' before acting to get accurate data-agent-id selectors."
    )
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["open_page", "observe", "click", "type", "select", "extract_text", "verify_state", "screenshot", "drag_and_drop", "scroll_down", "scroll_up", "new_tab", "switch_tab", "close_tab"],
                "description": "The browser action to perform."
            },
            "url": {"type": "string", "description": "Required for 'open_page'."},
            "selector": {"type": "string", "description": "CSS selector, Text selector (e.g., text='Login'), or data-agent-id."},
            "value": {"type": "string", "description": "Text value for 'type', 'select', 'verify_state', or drop target."},
            "tab_index": {"type": "integer", "description": "Index of tab for 'switch_tab' or 'close_tab'."},
            "is_critical": {"type": "boolean", "description": "Set to true for high-risk actions (delete, approve, submit financial data). Requires human approval."}
        },
        "required": ["action"]
    }

    def requires_approval(self, args: dict) -> bool:
        # 11. Risk-Based Actions
        return args.get("is_critical") is True
        
    def _is_allowed_url(self, url: str) -> bool:
        try:
            domain = urlparse(url).hostname
            if not domain:
                return False
            return any(domain.endswith(d) for d in ALLOWED_DOMAINS)
        except Exception:
            return False

    async def _auto_heal_locate(self, selector: str, page):
        """3. Auto-Healing Locators: Tries multiple locator strategies safely."""
        strategies = [
            selector,  # Exact selector provided by LLM (usually data-agent-id)
            f"text='{selector}'",  # Exact text match
            f"id={selector}",  # ID match
            f"role=button[name='{selector}']", # Accessible role
            f"label='{selector}'"
        ]
        
        for strategy in strategies:
            try:
                el = page.locator(strategy).first
                if await el.count() > 0:
                    return el
            except Exception:
                continue
        return None

    async def execute(self, action: str, **kwargs) -> ToolResult:
        try:
            import playwright
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        except ImportError:
            return ToolResult(success=False, error="Dependency missing: playwright is not installed.")
            
        run_id = kwargs.get("run_id", "default")
        try:
            page, context = await _ensure_started(run_id)
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to start browser: {e}")

        selector = kwargs.get("selector")
        value = kwargs.get("value")
        tab_index = kwargs.get("tab_index", 0)
        approval_granted = kwargs.get("approval_granted", False)

        # 4. Smart Retry mechanism wrapper
        retry_count = 0
        while retry_count < MAX_BROWSER_RETRIES:
            try:
                if action == "open_page":
                    url = kwargs.get("url")
                    if not url: return ToolResult(success=False, error="URL required")
                    if not self._is_allowed_url(url):
                        return ToolResult(success=False, error=f"Domain {url} not in allowed security list.")
                        
                    await page.goto(url, timeout=ACTION_TIMEOUT, wait_until="networkidle")
                    return ToolResult(success=True, data={"url": page.url, "title": await page.title()})
                    
                elif action == "observe":
                    # 1. Standardized Browser Observation & 2. Visual Element Highlighting
                    show_overlay = os.environ.get("BROWSER_DEBUG_OVERLAY", "true").lower() == "true"
                    
                    js_script = f"""
                    () => {{
                        document.querySelectorAll('.ai-bounding-box').forEach(e => e.remove());
                        const elements = Array.from(document.querySelectorAll('a, button, input, select, textarea, tr.employee-row'));
                        
                        elements.forEach((el, i) => {{
                            el.setAttribute('data-agent-id', i);
                            const rect = el.getBoundingClientRect();
                            if({str(show_overlay).lower()} && rect.width > 0 && rect.height > 0) {{
                                const box = document.createElement('div');
                                box.className = 'ai-bounding-box';
                                box.style.position = 'fixed';
                                box.style.top = rect.top + 'px';
                                box.style.left = rect.left + 'px';
                                box.style.width = rect.width + 'px';
                                box.style.height = rect.height + 'px';
                                box.style.border = '2px solid red';
                                box.style.zIndex = '999999';
                                box.style.pointerEvents = 'none';
                                
                                const label = document.createElement('span');
                                label.innerText = '[' + i + ']';
                                label.style.position = 'absolute';
                                label.style.top = '-15px';
                                label.style.left = '0';
                                label.style.background = 'red';
                                label.style.color = 'white';
                                label.style.fontSize = '12px';
                                box.appendChild(label);
                                document.body.appendChild(box);
                            }}
                        }});
                        
                        return elements.map(el => ({{
                            selector: `[data-agent-id="${{el.getAttribute('data-agent-id')}}"]`,
                            tag: el.tagName.toLowerCase(),
                            text: (el.innerText || el.value || el.placeholder || '').substring(0, 50).trim(),
                            ariaLabel: el.getAttribute('aria-label') || '',
                            name: el.getAttribute('name') || '',
                            role: el.getAttribute('role') || '',
                            disabled: el.disabled
                        }})).filter(el => !el.disabled && (el.text !== '' || el.ariaLabel !== ''));
                    }}
                    """
                    elements = await page.evaluate(js_script)
                    return ToolResult(success=True, data={
                        "url": page.url, 
                        "title": await page.title(),
                        "interactive_elements": elements
                    })
                    
                elif action == "click":
                    if not selector: return ToolResult(success=False, error="Selector required")
                    el = await self._auto_heal_locate(selector, page)
                    if not el:
                        raise PlaywrightTimeoutError(f"Auto-healing failed. Could not locate element: {selector}")
                        
                    # Code-based Risk Assessment
                    el_text = (await el.inner_text()).lower()
                    el_aria = (await el.get_attribute("aria-label") or "").lower()
                    is_dangerous = any(kw in el_text or kw in el_aria for kw in ["delete", "remove", "approve", "submit", "pay"])
                    if is_dangerous and not approval_granted:
                        return ToolResult(success=False, error="Safety violation: Clicking this button requires human approval due to its label/function.")
                        
                    before_url = page.url
                    try:
                        await el.click(timeout=ACTION_TIMEOUT)
                    except Exception:
                        await el.click(timeout=2000, force=True)
                        
                    try:
                        await page.wait_for_load_state("networkidle", timeout=2000)
                    except: pass
                    
                    state_changed = (before_url != page.url)
                    return ToolResult(success=True, data={
                        "clicked": selector, 
                        "url_changed": state_changed, 
                        "current_url": page.url
                    })
                    
                elif action == "type":
                    if not selector or value is None: return ToolResult(success=False, error="Selector and value required")
                    el = await self._auto_heal_locate(selector, page)
                    if not el:
                        raise PlaywrightTimeoutError(f"Auto-healing failed. Could not locate element: {selector}")
                    
                    try:
                        await el.fill(str(value), timeout=ACTION_TIMEOUT)
                    except Exception:
                        await el.focus(timeout=2000)
                        await page.keyboard.type(str(value), delay=50)
                        
                    return ToolResult(success=True, data={"typed": selector, "value": value})
                    
                elif action == "select":
                    if not selector or value is None: return ToolResult(success=False, error="Selector and value required")
                    el = await self._auto_heal_locate(selector, page)
                    if not el:
                        raise PlaywrightTimeoutError(f"Auto-healing failed. Could not locate element: {selector}")
                    await el.select_option(str(value), timeout=ACTION_TIMEOUT)
                    return ToolResult(success=True, data={"selected": selector, "value": value})
                    
                elif action == "extract_text":
                    if not selector: return ToolResult(success=False, error="Selector required")
                    el = await self._auto_heal_locate(selector, page)
                    if not el:
                        raise PlaywrightTimeoutError(f"Auto-healing failed. Could not locate element: {selector}")
                    text = await el.inner_text()
                    return ToolResult(success=True, data={"text": text})
                    
                elif action == "verify_state":
                    if not selector or value is None: return ToolResult(success=False, error="Selector and expected value required")
                    el = await self._auto_heal_locate(selector, page)
                    if not el: return ToolResult(success=True, data={"verified": False, "error": "Element not found for verification"})
                    actual_text = await el.inner_text()
                    is_match = (str(value).strip().lower() in actual_text.strip().lower())
                    return ToolResult(success=True, data={"verified": is_match, "expected": value, "actual": actual_text})
                    
                elif action == "screenshot":
                    import base64
                    screenshot_bytes = await page.screenshot(full_page=True, timeout=ACTION_TIMEOUT)
                    b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    return ToolResult(success=True, data={"screenshot_taken": True, "base64_preview": b64[:50] + "..."})
                    
                elif action == "drag_and_drop":
                    if not selector or not value: return ToolResult(success=False, error="Selector and value (target selector) required")
                    await page.drag_and_drop(selector, str(value), timeout=ACTION_TIMEOUT)
                    return ToolResult(success=True, data={"dragged": selector, "dropped_on": value})
                    
                elif action == "scroll_down":
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    return ToolResult(success=True, data={"scrolled": "down"})
                    
                elif action == "scroll_up":
                    await page.evaluate("window.scrollBy(0, -window.innerHeight)")
                    return ToolResult(success=True, data={"scrolled": "up"})
                    
                elif action == "new_tab":
                    page = await context.new_page()
                    _sessions[run_id]["page"] = page
                    return ToolResult(success=True, data={"message": "New tab opened", "total_tabs": len(context.pages)})
                    
                elif action == "switch_tab":
                    if tab_index < 0 or tab_index >= len(context.pages):
                        return ToolResult(success=False, error=f"Invalid tab index: {tab_index}")
                    page = context.pages[tab_index]
                    _sessions[run_id]["page"] = page
                    await page.bring_to_front()
                    return ToolResult(success=True, data={"switched_to_tab": tab_index, "url": page.url})
                    
                elif action == "close_tab":
                    if len(context.pages) <= 1:
                        return ToolResult(success=False, error="Cannot close the only open tab.")
                    await page.close()
                    page = context.pages[0] # Fallback to first tab
                    _sessions[run_id]["page"] = page
                    return ToolResult(success=True, data={"message": "Tab closed", "total_tabs": len(context.pages)})
                    
                return ToolResult(success=False, error=f"Unknown action: {action}")
                
            except PlaywrightTimeoutError:
                retry_count += 1
                logger.warning(f"Browser timeout on attempt {retry_count} for action {action}")
                if retry_count >= MAX_BROWSER_RETRIES:
                    return ToolResult(success=False, error=f"Action '{action}' failed after {MAX_BROWSER_RETRIES} retries. Re-observe the page and try a different locator.")
                await asyncio.sleep(1) # Small delay before retry
                
            except Exception as e:
                return ToolResult(success=False, error=f"Browser action failed: {str(e)}")
