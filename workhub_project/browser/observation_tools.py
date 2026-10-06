"""
Compact Structured Observation Tools for Autonomous LLM Agents.
"""

import time
import base64
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
from .element_resolver import ElementResolver

logger = logging.getLogger(__name__)

class ObservationTools:
    @staticmethod
    async def observe_page(page: Page, show_overlay: bool = True) -> Dict[str, Any]:
        """
        Observes the current page and returns a compact structured summary of interactive elements,
        forms, active view, and page state.
        """
        url = page.url
        title = await page.title()
        
        js_observe = f"""
        () => {{
            document.querySelectorAll('.ai-bounding-box').forEach(e => e.remove());
            const interactive = Array.from(document.querySelectorAll('a, button, input, select, textarea, [data-view], [data-testid], tr.employee-row, tr.expense-row, tr.task-row'));
            
            interactive.forEach((el, i) => {{
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
                    box.style.border = '2px solid #2563eb';
                    box.style.zIndex = '999999';
                    box.style.pointerEvents = 'none';
                    document.body.appendChild(box);
                }}
            }});

            return interactive.map(el => ({{
                id: el.getAttribute('data-agent-id'),
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || '',
                name: el.getAttribute('name') || '',
                text: (el.innerText || el.value || el.placeholder || '').substring(0, 60).trim(),
                ariaLabel: el.getAttribute('aria-label') || '',
                dataView: el.getAttribute('data-view') || '',
                dataTestId: el.getAttribute('data-testid') || '',
                disabled: el.disabled || false
            }})).filter(el => !el.disabled && (el.text !== '' || el.ariaLabel !== '' || el.dataView !== '' || el.dataTestId !== ''));
        }}
        """
        elements = await page.evaluate(js_observe)
        
        # Detect active modal or dialog if present
        active_modal = await page.evaluate("""
        () => {
            const openModals = Array.from(document.querySelectorAll('.modal-overlay:not(.hidden), dialog[open]'));
            if (openModals.length > 0) {
                const m = openModals[0];
                const header = m.querySelector('h2, h3, .modal-header');
                return {
                    is_open: true,
                    title: header ? header.innerText.trim() : 'Modal Dialog'
                };
            }
            return { is_open: false };
        }
        """)

        # Extract breadcrumbs / navigation
        active_nav = await page.evaluate("""
        () => {
            const active = document.querySelector('.nav-item.active');
            return active ? active.innerText.trim() : 'Dashboard';
        }
        """)

        # Compute DOM state hash
        content = await page.content()
        dom_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

        return {
            "url": url,
            "title": title,
            "active_view": active_nav,
            "dom_hash": dom_hash,
            "modal": active_modal,
            "interactive_elements_count": len(elements),
            "elements": elements
        }

    @staticmethod
    async def inspect_form(page: Page, form_target: Optional[str] = None) -> Dict[str, Any]:
        """
        Discovers and returns structured field definitions, types, options, and required statuses of any form.
        """
        js_inspect_form = """
        (formSelector) => {
            let form = formSelector ? document.querySelector(formSelector) : document.querySelector('form, .modal:not(.hidden), #view-container');
            if (!form) return { error: "No active form or container found." };

            const titleEl = form.querySelector('h2, h3, .modal-header, .form-title');
            const title = titleEl ? titleEl.innerText.trim() : 'Active Form';

            const inputs = Array.from(form.querySelectorAll('input:not([type="hidden"]), select, textarea'));
            const fields = inputs.map(el => {
                let label = '';
                if (el.id) {
                    const l = document.querySelector(`label[for="${el.id}"]`);
                    if (l) label = l.innerText.trim();
                }
                if (!label) {
                    const parentLabel = el.closest('label');
                    if (parentLabel) label = parentLabel.innerText.replace(el.value || '', '').trim();
                }
                if (!label) {
                    label = el.getAttribute('placeholder') || el.getAttribute('name') || el.getAttribute('aria-label') || el.id || 'Field';
                }

                let options = [];
                if (el.tagName.toLowerCase() === 'select') {
                    options = Array.from(el.querySelectorAll('option')).map(o => o.innerText.trim()).filter(t => t !== '');
                }

                return {
                    name: el.getAttribute('name') || el.id || '',
                    label: label,
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type') || el.tagName.toLowerCase(),
                    value: el.value || '',
                    required: el.required || el.classList.contains('required'),
                    options: options
                };
            });

            const buttons = Array.from(form.querySelectorAll('button, input[type="submit"]')).map(b => ({
                text: b.innerText.trim() || b.value || 'Submit',
                type: b.getAttribute('type') || 'button',
                action: b.getAttribute('data-action') || b.id || ''
            }));

            return {
                form_title: title,
                fields_count: fields.length,
                fields: fields,
                actions: buttons
            };
        }
        """
        return await page.evaluate(js_inspect_form, form_target)

    @staticmethod
    async def get_page_state(page: Page) -> Dict[str, Any]:
        """Returns compact state overview of the active page."""
        url = page.url
        title = await page.title()
        content = await page.content()
        dom_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
        
        return {
            "url": url,
            "title": title,
            "dom_hash": dom_hash,
            "timestamp": time.time()
        }

    @staticmethod
    async def get_visible_text(page: Page, selector: Optional[str] = None) -> str:
        """Extracts visible inner text from page or specified selector."""
        if selector:
            loc, _ = await ElementResolver.resolve(selector, page)
            if loc:
                return (await loc.inner_text()).strip()
        return (await page.inner_text("body")).strip()

    @staticmethod
    async def take_screenshot(page: Page, filename: Optional[str] = None) -> Dict[str, Any]:
        """Captures full-page PNG screenshot and saves to disk."""
        screenshots_dir = Path("runs/screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        fname = filename or f"screenshot_{int(time.time()*1000)}.png"
        filepath = screenshots_dir / fname
        
        bytes_data = await page.screenshot(full_page=True, path=str(filepath))
        b64 = base64.b64encode(bytes_data).decode('utf-8')
        
        return {
            "screenshot_taken": True,
            "file_path": str(filepath.resolve()),
            "filename": fname,
            "preview_b64": b64[:60] + "..."
        }
