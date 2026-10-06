"""
========================================================================================
 AGENTIC BROWSER AUTOMATION & RECOVERY LAYER
========================================================================================
File Path: ai_worker_project/tools/browser.py

Features:
  1. Browser Health & Watchdog (browser_health, get_page_state, detect_network_idle)
  2. Intelligent Waiting without fixed sleeps (wait_for_condition, dom_stable, disappear)
  3. Screenshot & Visual Change Verification (screenshot_verify, detect_visual_change)
  4. 6-Tier Auto-Healing Locators (data-testid, ARIA role, text, placeholder, CSS, XPath)
  5. Dual-Layer Action Verifier (Browser UI State + SQLite DB backend validation)
  6. Graduated 4-Level Retry & Recovery Manager (Locator -> Refresh -> Reopen -> Recover)
  7. Stuck-Agent Loop Detector & Auto-Healing (detect_stuck_execution, recover_browser_state)
  8. Idempotency & Session Persistence Checkpointing (runs/browser_checkpoints/)
========================================================================================
"""

import os
import sys
import re
import json
import time
import hashlib
import logging
import asyncio
from pathlib import Path
from urllib.parse import urlparse
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel

logger = logging.getLogger(__name__)

# Security & Safety
ALLOWED_DOMAINS = ["workhub.local", "localhost", "127.0.0.1", "0.0.0.0", "example.com", "centralign.local"]
MAX_BROWSER_RETRIES = 3
ACTION_TIMEOUT = 10000

_playwright = None
_sessions = {}
_execution_history = {}  # run_id -> list of state snapshots for stuck detection
_checkpoints_dir = Path("runs/browser_checkpoints")
_screenshots_dir = Path("runs/screenshots")

_checkpoints_dir.mkdir(parents=True, exist_ok=True)
_screenshots_dir.mkdir(parents=True, exist_ok=True)


async def _ensure_started(run_id: str):
    global _playwright, _sessions
    
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

    current_loop = asyncio.get_running_loop()
    if _playwright is not None:
        try:
            pw_loop = getattr(_playwright, "_loop", None)
            if pw_loop is not None and pw_loop != current_loop:
                _playwright = None
        except Exception:
            _playwright = None

    if run_id not in _sessions or _sessions[run_id]["page"].is_closed():
        from playwright.async_api import async_playwright
        
        # Ensure fresh playwright driver for this event loop
        if _playwright is None:
            _playwright = await async_playwright().start()
            
        headless_mode = os.environ.get("HEADLESS", "false").lower() == "true"
        context = None
        
        # Strategy 1: Persistent context with isolated profile
        try:
            profile_dir = f"./browser_session_{run_id}"
            context = await _playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=headless_mode,
                slow_mo=800,
                viewport=None,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
        except Exception:
            # Strategy 2: Standard non-persistent context
            try:
                browser = await _playwright.chromium.launch(
                    headless=headless_mode,
                    slow_mo=800,
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                context = await browser.new_context(viewport=None)
            except Exception:
                # Strategy 3: Complete driver re-instantiation
                try:
                    _playwright = await async_playwright().start()
                    browser = await _playwright.chromium.launch(
                        headless=headless_mode,
                        slow_mo=800,
                        args=["--start-maximized", "--disable-blink-features=AutomationControlled", "--no-sandbox"]
                    )
                    context = await browser.new_context(viewport=None)
                except Exception as inner_e:
                    raise RuntimeError(f"Playwright browser launch failed: {inner_e}")

        page = context.pages[0] if context.pages else await context.new_page()
        try:
            await page.bring_to_front()
        except Exception:
            pass
        _sessions[run_id] = {"context": context, "page": page, "last_dom_hash": "", "stuck_count": 0}
        
    return _sessions[run_id]["page"], _sessions[run_id]["context"]






async def close_browser_session(run_id: str = "default"):
    """Closes browser session and cleans up resources for run_id."""
    global _sessions
    if run_id in _sessions:
        try:
            await _sessions[run_id]["context"].close()
        except Exception:
            pass
        del _sessions[run_id]


class BrowserTool(Tool):
    name = "browser"
    description = (
        "Enterprise-grade browser automation & self-healing recovery layer. "
        "Actions: "
        "'open_page', 'observe', 'click', 'type', 'select', 'extract_text', 'verify_state', "
        "'screenshot', 'wait_for_condition', 'browser_health', 'detect_visual_change', "
        "'verify_action_result', 'recover_browser_state', 'detect_stuck_execution', "
        "'drag_and_drop', 'scroll_down', 'scroll_up', 'new_tab', 'switch_tab', 'close_tab'."
    )
    risk_level = RiskLevel.LOW

    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "open_page", "observe", "click", "type", "select", "extract_text", 
                    "verify_state", "screenshot", "wait_for_condition", "browser_health", 
                    "detect_visual_change", "verify_action_result", "recover_browser_state", 
                    "detect_stuck_execution", "drag_and_drop", "scroll_down", "scroll_up", 
                    "new_tab", "switch_tab", "close_tab"
                ],
                "description": "The browser action or recovery operation to perform."
            },
            "url": {"type": "string", "description": "Target URL for 'open_page' or verification."},
            "selector": {"type": "string", "description": "Element selector (data-agent-id, text, CSS, XPath, or ARIA)."},
            "value": {"type": "string", "description": "Input value for 'type', 'select', 'verify_state', or condition target."},
            "condition_type": {
                "type": "string",
                "enum": ["selector", "text", "url_change", "network_idle", "dom_stable", "disappear"],
                "description": "Condition type for 'wait_for_condition'."
            },
            "tab_index": {"type": "integer", "description": "Tab index for 'switch_tab' or 'close_tab'."},
            "db_table": {"type": "string", "description": "Database table name for dual-layer 'verify_action_result'."},
            "db_query": {"type": "string", "description": "SQL verification query for dual-layer 'verify_action_result'."},
            "is_critical": {"type": "boolean", "description": "Set to true for high-risk mutations requiring authorization."}
        },
        "required": ["action"]
    }

    def requires_approval(self, args: dict) -> bool:
        return args.get("is_critical") is True

    def _is_allowed_url(self, url: str) -> bool:
        try:
            domain = urlparse(url).hostname
            if not domain:
                return False
            return any(domain.endswith(d) for d in ALLOWED_DOMAINS)
        except Exception:
            return False

    async def _resolve_semantic_target(self, target: str, page, target_id: str = None, tag_hint: str = None):
        """
        Semantic Target Resolver:
        Resolves human-readable semantic targets (e.g. 'Open Task', 'Status', 'Approve', 'Sarah Connor')
        without requiring the LLM to generate fragile CSS or XPath selectors.
        """
        if not target and not target_id:
            return None

        clean_target = (target or "").strip()
        
        # 1. If target_id is provided, try direct data-id or ID match
        if target_id:
            tid = str(target_id).strip()
            locators = [
                page.locator(f"[data-id='{tid}']"),
                page.locator(f"[data-emp-id='{tid}']"),
                page.locator(f"[data-testid='{tid}']"),
                page.locator(f"#{tid}"),
                page.locator(f"[data-agent-id='{tid}']")
            ]
            for loc in locators:
                try:
                    if await loc.count() > 0:
                        return loc.first
                except Exception:
                    pass

        # 2. Check active modal context first if modal is open
        try:
            modal = page.locator(".modal-overlay:not(.hidden), #approval-modal:not(.hidden)").first
            if await modal.count() > 0 and await modal.is_visible():
                # Check modal buttons and fields
                if tag_hint in ["button", None]:
                    btn = modal.get_by_role("button", name=re.compile(re.escape(clean_target), re.IGNORECASE))
                    if await btn.count() > 0:
                        return btn.first
                    # Keyword matching in modal buttons
                    for word in clean_target.split():
                        if len(word) > 2:
                            w_btn = modal.get_by_role("button", name=re.compile(re.escape(word), re.IGNORECASE))
                            if await w_btn.count() > 0:
                                return w_btn.first

                if tag_hint in ["select", "input", "textarea", None]:
                    fld = modal.get_by_label(re.compile(re.escape(clean_target), re.IGNORECASE))
                    if await fld.count() > 0:
                        return fld.first
                    # Keyword matching for fields
                    for word in clean_target.split():
                        if len(word) > 2:
                            w_fld = modal.get_by_label(re.compile(re.escape(word), re.IGNORECASE))
                            if await w_fld.count() > 0:
                                return w_fld.first
                    fld2 = modal.locator(f"select#{clean_target}, input#{clean_target}, [name='{clean_target}']")
                    if await fld2.count() > 0:
                        return fld2.first
        except Exception:
            pass

        # 3. Try Playwright standard semantic locators on full page
        strategies = []
        target_lower = clean_target.lower()

        # A. Navigation & Module Links (High Priority)
        strategies.append(page.locator(f".nav-item[data-view='{target_lower}']"))
        strategies.append(page.locator(f".nav-item[data-testid='nav-{target_lower}']"))
        strategies.append(page.locator(f"a.nav-item:has-text('{clean_target}')"))
        strategies.append(page.get_by_role("link", name=re.compile(f"^{re.escape(clean_target)}$", re.I)))
        strategies.append(page.get_by_role("link", name=re.compile(re.escape(clean_target), re.I)))

        # B. Form controls by label & placeholder (WAI-ARIA Standard)
        if tag_hint in ["input", "select", "textarea", None]:
            strategies.append(page.get_by_label(clean_target, exact=True))
            strategies.append(page.get_by_label(re.compile(f"^{re.escape(clean_target)}$", re.IGNORECASE)))
            strategies.append(page.get_by_label(re.compile(re.escape(clean_target), re.IGNORECASE)))
            strategies.append(page.get_by_placeholder(clean_target))
            strategies.append(page.get_by_placeholder(re.compile(re.escape(clean_target), re.IGNORECASE)))

        # C. Exact & Regex Buttons / Tabs by role
        if tag_hint in ["button", None]:
            strategies.append(page.get_by_role("button", name=clean_target, exact=True))
            strategies.append(page.get_by_role("button", name=re.compile(f"^{re.escape(clean_target)}$", re.IGNORECASE)))
            strategies.append(page.get_by_role("button", name=re.compile(re.escape(clean_target), re.IGNORECASE)))
            strategies.append(page.get_by_role("tab", name=clean_target))

        # D. Test ID and ARIA attributes
        strategies.append(page.get_by_test_id(clean_target))
        strategies.append(page.locator(f"[aria-label='{clean_target}']"))
        strategies.append(page.locator(f"[aria-label*='{clean_target}' i]"))
        strategies.append(page.locator(f"[data-view='{target_lower}']"))

        # E. Direct Text match on interactive items first, then general
        strategies.append(page.locator(f"button:has-text('{clean_target}'), a:has-text('{clean_target}'), [role='button']:has-text('{clean_target}')"))
        strategies.append(page.get_by_text(clean_target, exact=True))
        strategies.append(page.get_by_text(clean_target, exact=False))

        # F. Direct ID or CSS selector fallback
        if clean_target.startswith("#") or clean_target.startswith(".") or "[" in clean_target:
            strategies.append(page.locator(clean_target))
        else:
            strategies.append(page.locator(f"#{clean_target}"))
            strategies.append(page.locator(f"#{clean_target}"))

        for loc in strategies:
            try:
                first_match = loc.first
                if await first_match.count() > 0 and await first_match.is_visible(timeout=400):
                    return first_match
            except Exception:
                continue

        # Last resort: first match even if still rendering
        for loc in strategies:
            try:
                first_match = loc.first
                if await first_match.count() > 0:
                    return first_match
            except Exception:
                continue

    async def _show_visual_indicator(self, page, el, action_type: str, label_text: str = ""):
        """
        Renders a glowing visual indicator and action badge on the targeted element
        so the user can clearly see which element the AI is clicking, typing, or selecting in real-time.
        """
        try:
            js = """
            ([element, actionType, labelText]) => {
                if (!element) return;
                
                // Remove previous indicators
                document.querySelectorAll('.ai-visual-indicator-badge, .ai-visual-indicator-ring').forEach(e => e.remove());
                
                const rect = element.getBoundingClientRect();
                const colors = {
                    'click': { border: '#00E5FF', bg: 'rgba(0, 229, 255, 0.22)', badge: '#00B4D8', text: '#FFFFFF', icon: '👆' },
                    'type': { border: '#FFD700', bg: 'rgba(255, 215, 0, 0.22)', badge: '#D97706', text: '#FFFFFF', icon: '✍️' },
                    'select': { border: '#10B981', bg: 'rgba(16, 185, 129, 0.22)', badge: '#059669', text: '#FFFFFF', icon: '🔽' }
                };
                const theme = colors[actionType] || colors['click'];
                
                // 1. Highlight Ring
                const ring = document.createElement('div');
                ring.className = 'ai-visual-indicator-ring';
                ring.style.cssText = `
                    position: fixed;
                    left: ${Math.max(0, rect.left - 4)}px;
                    top: ${Math.max(0, rect.top - 4)}px;
                    width: ${rect.width + 8}px;
                    height: ${rect.height + 8}px;
                    border: 3px solid ${theme.border};
                    background: ${theme.bg};
                    border-radius: 6px;
                    pointer-events: none;
                    z-index: 999999;
                    box-shadow: 0 0 16px ${theme.border};
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
                    box-shadow: 0 4px 12px rgba(0,0,0,0.35);
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
                            0% { transform: scale(1); opacity: 0.9; }
                            100% { transform: scale(1.03); opacity: 1; box-shadow: 0 0 24px rgba(0,229,255,0.85); }
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
            await page.evaluate(js, [el, action_type, label_text[:35]])
            await asyncio.sleep(0.35)
        except Exception:
            pass

    async def _hide_visual_indicator(self, page):
        try:
            await page.evaluate("() => document.querySelectorAll('.ai-visual-indicator-badge, .ai-visual-indicator-ring').forEach(e => e.remove())")
        except Exception:
            pass

    async def _compute_dom_hash(self, page) -> str:
        """Computes a lightweight SHA-256 hash of the visible DOM state."""
        try:
            html = await page.content()
            return hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
        except Exception:
            return ""

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
            return ToolResult(success=False, error=f"Failed to start/attach browser: {e}")

        # Extract semantic target or legacy selector
        target = kwargs.get("target") or kwargs.get("selector") or kwargs.get("name") or kwargs.get("element") or ""
        target_id = kwargs.get("target_id") or kwargs.get("id") or None
        value = kwargs.get("value")
        condition_type = kwargs.get("condition_type", "selector")
        tab_index = kwargs.get("tab_index", 0)
        approval_granted = kwargs.get("approval_granted", False)

        # ----------------------------------------------------------------------
        # 1. BROWSER HEALTH & WATCHDOG
        # ----------------------------------------------------------------------
        if action == "browser_health":
            try:
                is_closed = page.is_closed()
                url = page.url if not is_closed else "N/A"
                title = await page.title() if not is_closed else "N/A"
                ready_state = await page.evaluate("() => document.readyState") if not is_closed else "closed"
                tabs_count = len(context.pages)
                dom_hash = await self._compute_dom_hash(page) if not is_closed else ""

                return ToolResult(success=True, data={
                    "status": "HEALTHY" if not is_closed else "CRASHED",
                    "url": url,
                    "title": title,
                    "ready_state": ready_state,
                    "active_tabs": tabs_count,
                    "dom_hash": dom_hash,
                    "responsive": True
                })
            except Exception as e:
                return ToolResult(success=False, error=f"Browser watchdog detected unhealthy state: {e}")

        # ----------------------------------------------------------------------
        # 2. INTELLIGENT WAITING (No fixed sleeps)
        # ----------------------------------------------------------------------
        elif action == "wait_for_condition":
            timeout_ms = kwargs.get("timeout", ACTION_TIMEOUT)
            start_w = time.time()
            try:
                if condition_type == "network_idle":
                    await page.wait_for_load_state("networkidle", timeout=timeout_ms)
                    return ToolResult(success=True, data={"condition": "network_idle", "elapsed_ms": int((time.time() - start_w)*1000)})

                elif condition_type == "dom_stable":
                    # Wait until DOM stops mutating for 300ms
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
                    return ToolResult(success=True, data={"condition": "dom_stable", "elapsed_ms": int((time.time() - start_w)*1000)})

                elif condition_type == "text":
                    if not value: return ToolResult(success=False, error="Value required for text condition")
                    await page.wait_for_selector(f":has-text('{value}')", timeout=timeout_ms)
                    return ToolResult(success=True, data={"condition": "text_found", "text": value})

                elif condition_type == "disappear":
                    if not target: return ToolResult(success=False, error="Target required for disappear condition")
                    el = await self._resolve_semantic_target(target, page, target_id=target_id)
                    if el:
                        await el.wait_for(state="detached", timeout=timeout_ms)
                    return ToolResult(success=True, data={"condition": "element_disappeared", "target": target})

                elif condition_type == "url_change":
                    expected_part = value or ""
                    await page.wait_for_url(lambda u: expected_part in u, timeout=timeout_ms)
                    return ToolResult(success=True, data={"condition": "url_changed", "current_url": page.url})

                else: # Default: target visible
                    if not target: return ToolResult(success=False, error="Target required")
                    el = await self._resolve_semantic_target(target, page, target_id=target_id)
                    if not el:
                        raise PlaywrightTimeoutError(f"Target '{target}' not found within {timeout_ms}ms")
                    return ToolResult(success=True, data={"condition": "target_visible", "target": target})

            except Exception as e:
                return ToolResult(success=False, error=f"wait_for_condition failed: {str(e)}")

        # ----------------------------------------------------------------------
        # 3. SCREENSHOT & VISUAL CHANGE VERIFICATION
        # ----------------------------------------------------------------------
        elif action == "detect_visual_change":
            current_hash = await self._compute_dom_hash(page)
            prev_hash = _sessions.get(run_id, {}).get("last_dom_hash", "")
            changed = (current_hash != prev_hash and prev_hash != "")
            _sessions[run_id]["last_dom_hash"] = current_hash

            return ToolResult(success=True, data={
                "visual_state_changed": changed,
                "current_dom_hash": current_hash,
                "previous_dom_hash": prev_hash
            })

        # ----------------------------------------------------------------------
        # 4. DUAL-LAYER ACTION VERIFIER (Browser UI + Database)
        # ----------------------------------------------------------------------
        elif action == "verify_action_result":
            # 1. UI Verification
            ui_verified = True
            ui_details = {}
            if target and value:
                el = await self._resolve_semantic_target(target, page, target_id=target_id)
                if el:
                    actual_txt = await el.inner_text()
                    ui_verified = (str(value).lower() in actual_txt.lower())
                    ui_details = {"target": target, "expected": value, "actual": actual_txt, "match": ui_verified}
                else:
                    ui_verified = False
                    ui_details = {"target": target, "error": "Element not found"}

            # 2. Database Verification (if SQL query or table provided)
            db_verified = True
            db_details = {}
            db_query = kwargs.get("db_query")
            if db_query:
                try:
                    import sqlite3
                    conn = sqlite3.connect("workhub_project/database/company_database.sqlite")
                    cur = conn.cursor()
                    cur.execute(db_query)
                    rows = cur.fetchall()
                    conn.close()
                    db_verified = len(rows) > 0
                    db_details = {"query": db_query, "rows_found": len(rows), "sample": str(rows[:2])}
                except Exception as db_err:
                    db_verified = False
                    db_details = {"error": str(db_err)}

            overall_success = ui_verified and db_verified
            return ToolResult(success=overall_success, data={
                "verified": overall_success,
                "ui_verification": ui_details,
                "db_verification": db_details
            })

        # ----------------------------------------------------------------------
        # 5. STUCK EXECUTION DETECTOR & AUTO-RECOVERY
        # ----------------------------------------------------------------------
        elif action == "detect_stuck_execution":
            dom_hash = await self._compute_dom_hash(page)
            curr_url = page.url
            
            history = _execution_history.setdefault(run_id, [])
            history.append({"url": curr_url, "dom_hash": dom_hash, "time": time.time()})
            if len(history) > 10:
                history.pop(0)

            is_stuck = False
            if len(history) >= 3:
                last_3 = history[-3:]
                is_stuck = all(h["dom_hash"] == last_3[0]["dom_hash"] and h["url"] == last_3[0]["url"] for h in last_3)

            return ToolResult(success=True, data={
                "is_stuck": is_stuck,
                "cycles_monitored": len(history),
                "url": curr_url,
                "recommendation": "Invoke 'recover_browser_state' if is_stuck is True."
            })

        elif action == "recover_browser_state":
            strategy = kwargs.get("strategy", "refresh")
            curr_url = page.url
            try:
                if strategy == "refresh":
                    await page.reload(wait_until="networkidle", timeout=ACTION_TIMEOUT)
                elif strategy == "reopen":
                    await page.goto(curr_url or "http://localhost:3000/index.html", wait_until="networkidle", timeout=ACTION_TIMEOUT)
                elif strategy == "reconnect":
                    await close_browser_session(run_id)
                    page, context = await _ensure_started(run_id)
                    await page.goto(curr_url or "http://localhost:3000/index.html", wait_until="networkidle", timeout=ACTION_TIMEOUT)
                
                new_hash = await self._compute_dom_hash(page)
                _sessions[run_id]["last_dom_hash"] = new_hash
                return ToolResult(success=True, data={"recovery_status": "RECOVERED", "strategy": strategy, "url": page.url})
            except Exception as rec_err:
                return ToolResult(success=False, error=f"Recovery failed: {rec_err}")

        # ----------------------------------------------------------------------
        # 6. CORE ACTIONS WITH SEMANTIC RESOLUTION & BOUNDED RETRIES
        # ----------------------------------------------------------------------
        MAX_ACTION_RETRIES = 2
        retry_count = 0
        while retry_count < MAX_ACTION_RETRIES:
            try:
                if action == "open_page":
                    url = kwargs.get("url")
                    if not url: return ToolResult(success=False, error="URL required")
                    if not self._is_allowed_url(url):
                        return ToolResult(success=False, error=f"Domain {url} not in allowed security list.")
                        
                    await page.goto(url, timeout=ACTION_TIMEOUT, wait_until="networkidle")
                    dom_hash = await self._compute_dom_hash(page)
                    _sessions[run_id]["last_dom_hash"] = dom_hash

                    # Save checkpoint
                    chk_file = _checkpoints_dir / f"session_{run_id}.json"
                    chk_file.write_text(json.dumps({"url": page.url, "dom_hash": dom_hash, "time": time.time()}))

                    return ToolResult(success=True, data={
                        "success": True,
                        "url": page.url,
                        "title": await page.title(),
                        "dom_hash": dom_hash
                    })

                elif action == "observe":
                    # Structured, Modal-Aware Observer
                    js_structure_script = """
                    () => {
                        const isModalOpen = !document.getElementById('approval-modal')?.classList.contains('hidden') || 
                                            !document.getElementById('ai-modal')?.classList.contains('hidden');
                        
                        let currentView = 'Dashboard';
                        const activeNav = document.querySelector('.nav-item.active');
                        if (activeNav) currentView = activeNav.innerText.trim();

                        if (isModalOpen) {
                            const modal = document.getElementById('approval-modal');
                            const modalTitle = modal.querySelector('.modal-header h3')?.innerText.trim() || 'Active Modal';
                            
                            const fields = [];
                            modal.querySelectorAll('input, select, textarea').forEach(el => {
                                const label = el.getAttribute('aria-label') || el.name || el.id || 'Field';
                                const type = el.tagName.toLowerCase();
                                const val = el.value || '';
                                let options = [];
                                if (type === 'select') {
                                    options = Array.from(el.querySelectorAll('option')).map(o => o.value);
                                }
                                fields.push({ target: label, id: el.id, type: type, current_value: val, options: options });
                            });

                            const actions = [];
                            modal.querySelectorAll('button:not(.close-modal)').forEach(btn => {
                                if (btn.style.display !== 'none') {
                                    actions.push({ target: btn.innerText.trim() || btn.getAttribute('aria-label') || 'Button', id: btn.id });
                                }
                            });

                            return {
                                context: 'MODAL_OPEN',
                                view: currentView,
                                modal_title: modalTitle,
                                fields: fields,
                                actions: actions
                            };
                        }

                        // Normal Page Context
                        const navTabs = Array.from(document.querySelectorAll('.nav-item')).map(n => ({
                            target: n.innerText.trim(),
                            view_name: n.getAttribute('data-view') || ''
                        }));

                        const pageActions = [];
                        document.querySelectorAll('.card-header button, #main-content > div > button, #view-container .card-header button').forEach(b => {
                            const txt = b.innerText.trim() || b.getAttribute('aria-label') || 'Button';
                            if (!pageActions.some(a => a.id === b.id && a.target === txt)) {
                                pageActions.push({ target: txt, id: b.id });
                            }
                        });

                        const formFields = [];
                        document.querySelectorAll('#view-container input, #view-container select, #view-container textarea').forEach(el => {
                            if (el.type === 'hidden') return;
                            let label = el.getAttribute('aria-label') || el.name || el.placeholder || el.id;
                            const labelEl = document.querySelector(`label[for="${el.id}"]`) || el.closest('label');
                            if (labelEl) label = labelEl.innerText.trim();
                            const type = el.tagName.toLowerCase();
                            const val = el.value || '';
                            let options = [];
                            if (type === 'select') {
                                options = Array.from(el.querySelectorAll('option')).map(o => o.value);
                            }
                            formFields.push({ target: label, id: el.id, type: type, current_value: val, disabled: el.disabled, options: options });
                        });

                        const tableRows = [];
                        document.querySelectorAll('.data-table tbody tr').forEach((tr, i) => {
                            const rowName = tr.getAttribute('aria-label') || `Row ${i+1}`;
                            const buttons = Array.from(tr.querySelectorAll('button')).map(b => ({
                                target: b.getAttribute('aria-label') || b.innerText.trim() || 'Action',
                                id: b.getAttribute('data-id') || b.id || ''
                            }));
                            const textSummary = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim()).join(' | ');
                            tableRows.push({ name: rowName, summary: textSummary.substring(0, 100), actions: buttons });
                        });

                        return {
                            context: 'PAGE',
                            view: currentView,
                            navigation_tabs: navTabs,
                            page_actions: pageActions,
                            form_fields: formFields,
                            table_rows: tableRows.slice(0, 20)
                        };
                    }
                    """
                    obs_data = await page.evaluate(js_structure_script)
                    dom_hash = await self._compute_dom_hash(page)
                    _sessions[run_id]["last_dom_hash"] = dom_hash

                    return ToolResult(success=True, data={
                        "url": page.url,
                        "title": await page.title(),
                        "dom_hash": dom_hash,
                        "observation": obs_data
                    })

                elif action == "click":
                    if not target: return ToolResult(success=False, error="Target or selector required for click")
                    el = await self._resolve_semantic_target(target, page, target_id=target_id, tag_hint="button")
                    if not el:
                        raise PlaywrightTimeoutError(f"Could not locate clickable target: '{target}' (ID: {target_id})")

                    # Highlight element with animated AI badge before interaction
                    await self._show_visual_indicator(page, el, action_type="click", label_text=target)

                    before_url = page.url
                    before_hash = await self._compute_dom_hash(page)

                    try:
                        await el.click(timeout=ACTION_TIMEOUT)
                    except Exception:
                        await el.click(timeout=2000, force=True)

                    await self._hide_visual_indicator(page)

                    try:
                        await page.wait_for_load_state("networkidle", timeout=1200)
                    except Exception:
                        pass

                    after_hash = await self._compute_dom_hash(page)
                    _sessions[run_id]["last_dom_hash"] = after_hash

                    # Check if modal was opened
                    modal_opened = await page.evaluate("() => !document.getElementById('approval-modal')?.classList.contains('hidden')")

                    return ToolResult(success=True, data={
                        "success": True,
                        "action": "click",
                        "target": target,
                        "modal_opened": modal_opened,
                        "page_changed": (before_hash != after_hash or before_url != page.url),
                        "current_url": page.url
                    })

                elif action == "type":
                    if not target or value is None: return ToolResult(success=False, error="Target and value required for type")
                    el = await self._resolve_semantic_target(target, page, target_id=target_id, tag_hint="input")
                    if not el:
                        raise PlaywrightTimeoutError(f"Could not locate input target: '{target}'")

                    # Highlight input with animated AI typing badge
                    await self._show_visual_indicator(page, el, action_type="type", label_text=f"{target} → '{value}'")

                    try:
                        await el.fill("", timeout=ACTION_TIMEOUT)
                        if hasattr(el, "press_sequentially"):
                            await el.press_sequentially(str(value), delay=50)
                        else:
                            await el.type(str(value), delay=50)
                    except Exception:
                        try:
                            await el.focus(timeout=1500)
                            await page.keyboard.type(str(value), delay=50)
                        except Exception:
                            await el.fill(str(value), timeout=ACTION_TIMEOUT)

                    await self._hide_visual_indicator(page)

                    return ToolResult(success=True, data={"success": True, "action": "type", "target": target, "value": value})

                elif action == "select":
                    if not target or value is None: return ToolResult(success=False, error="Target and value required for select")
                    el = await self._resolve_semantic_target(target, page, target_id=target_id, tag_hint="select")
                    if not el:
                        raise PlaywrightTimeoutError(f"Could not locate dropdown select target: '{target}'")

                    # Highlight select with animated AI dropdown badge
                    await self._show_visual_indicator(page, el, action_type="select", label_text=f"{target} → '{value}'")

                    val_str = str(value).strip()
                    selected = False

                    # Strategy 1: Direct value match
                    try:
                        await el.select_option(val_str, timeout=1200)
                        selected = True
                    except Exception:
                        pass

                    # Strategy 2: Direct label match
                    if not selected:
                        try:
                            await el.select_option(label=val_str, timeout=1200)
                            selected = True
                        except Exception:
                            pass

                    # Strategy 3: Case-insensitive / partial match among <option> tags
                    if not selected:
                        try:
                            options_js = """
                            ([selectEl, searchVal]) => {
                                if (!selectEl || selectEl.tagName !== 'SELECT') return null;
                                const lower = searchVal.toLowerCase();
                                const opts = Array.from(selectEl.options);
                                // Exact case-insensitive value or text
                                let found = opts.find(o => o.value.toLowerCase() === lower || o.text.toLowerCase() === lower);
                                if (!found) {
                                    // Prefix or partial match
                                    found = opts.find(o => o.value.toLowerCase().includes(lower) || o.text.toLowerCase().includes(lower) || lower.includes(o.value.toLowerCase()));
                                }
                                if (found) {
                                    selectEl.value = found.value;
                                    selectEl.dispatchEvent(new Event('change', { bubbles: true }));
                                    selectEl.dispatchEvent(new Event('input', { bubbles: true }));
                                    return found.value;
                                }
                                return null;
                            }
                            """
                            matched_val = await el.evaluate(options_js, val_str)
                            if matched_val is not None:
                                selected = True
                        except Exception:
                            pass

                    await self._hide_visual_indicator(page)
                    if not selected:
                        return ToolResult(success=False, error=f"Could not select option '{value}' in target '{target}'")

                    return ToolResult(success=True, data={"success": True, "action": "select", "target": target, "value": value})

                elif action == "extract_text":
                    if not target: return ToolResult(success=False, error="Target required for extract_text")
                    el = await self._resolve_semantic_target(target, page, target_id=target_id)
                    if not el:
                        raise PlaywrightTimeoutError(f"Could not locate target for extract_text: '{target}'")
                    text = await el.inner_text()
                    return ToolResult(success=True, data={"text": text})

                elif action == "verify_state":
                    if not target or value is None: return ToolResult(success=False, error="Target and expected value required")
                    el = await self._resolve_semantic_target(target, page, target_id=target_id)
                    if not el: return ToolResult(success=True, data={"verified": False, "error": "Element not found"})
                    actual_text = await el.inner_text()
                    is_match = (str(value).strip().lower() in actual_text.strip().lower())
                    return ToolResult(success=True, data={"verified": is_match, "expected": value, "actual": actual_text})

                elif action == "screenshot":
                    import base64
                    fname = kwargs.get("filename") or f"screenshot_{int(time.time())}.png"
                    filepath = _screenshots_dir / fname
                    screenshot_bytes = await page.screenshot(full_page=True, timeout=ACTION_TIMEOUT, path=str(filepath))
                    b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    return ToolResult(success=True, data={
                        "screenshot_taken": True,
                        "file_path": str(filepath.resolve()),
                        "filename": fname,
                        "base64_preview": b64[:50] + "..."
                    })

                elif action == "drag_and_drop":
                    if not selector or not value: return ToolResult(success=False, error="Selector and drop target required")
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
                    page = context.pages[0]
                    _sessions[run_id]["page"] = page
                    return ToolResult(success=True, data={"message": "Tab closed", "total_tabs": len(context.pages)})

                return ToolResult(success=False, error=f"Unknown action: {action}")

            except PlaywrightTimeoutError:
                retry_count += 1
                logger.warning(f"[Browser Recovery] Level {retry_count} triggered for action '{action}'")
                
                # Graduated Recovery Manager:
                if retry_count < MAX_BROWSER_RETRIES:
                    # Stabilize DOM and wait for UI animations
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=1000)
                    except Exception:
                        pass
                else:
                    return ToolResult(
                        success=False,
                        error=f"Action '{action}' failed to locate target '{target}'. Element may be labeled differently or inside a closed dialog."
                    )

            except Exception as e:
                return ToolResult(success=False, error=f"Browser action '{action}' error: {str(e)}")
