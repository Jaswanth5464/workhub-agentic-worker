"""
Smart Multi-Tier Element Resolver for Autonomous Browser Automation.
Resolves natural-language & semantic targets across 9 locator tiers.
"""

import re
import logging
from typing import Optional, Dict, Any, Tuple
from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)

class ElementResolver:
    @staticmethod
    async def resolve(target: str, page: Page) -> Tuple[Optional[Locator], Dict[str, Any]]:
        """
        Resolves a semantic target string to a Playwright Locator using progressive fallback:
        1. data-testid
        2. accessible role + accessible name
        3. aria-label
        4. associated label
        5. visible text / :has-text
        6. title / placeholder / name
        7. CSS selector
        8. XPath
        9. visual location (first interactive child)
        """
        if not target or not isinstance(target, str):
            return None, {"resolved": False, "error": "Target must be a non-empty string"}

        clean_target = target.strip()
        strategies = [
            # 1. data-testid / data-agent-id
            ("data_testid", f"[data-testid='{clean_target}']"),
            ("data_agent_id", f"[data-agent-id='{clean_target}']"),
            ("data_view", f"[data-view='{clean_target}']"),

            # 2. Accessible role + name
            ("aria_role_button", f"role=button[name='{clean_target}' i]"),
            ("aria_role_link", f"role=link[name='{clean_target}' i]"),
            ("aria_role_tab", f"role=tab[name='{clean_target}' i]"),
            ("aria_role_textbox", f"role=textbox[name='{clean_target}' i]"),
            ("aria_role_combobox", f"role=combobox[name='{clean_target}' i]"),
            ("aria_role_checkbox", f"role=checkbox[name='{clean_target}' i]"),

            # 3. aria-label
            ("aria_label", f"[aria-label='{clean_target}' i]"),
            ("aria_label_sub", f"[aria-label*='{clean_target}' i]"),

            # 4. Associated <label> or form field
            ("label_text", f"label:has-text('{clean_target}')"),

            # 5. Exact & substring text
            ("exact_text", f"text='{clean_target}'"),
            ("has_text_btn", f"button:has-text('{clean_target}')"),
            ("has_text_a", f"a:has-text('{clean_target}')"),
            ("has_text_any", f":has-text('{clean_target}')"),

            # 6. Placeholder / name / title
            ("placeholder", f"input[placeholder*='{clean_target}' i], textarea[placeholder*='{clean_target}' i]"),
            ("attr_name", f"[name='{clean_target}' i]"),
            ("attr_title", f"[title*='{clean_target}' i]"),
            ("id_match", f"#{clean_target}"),
            ("class_match", f".{clean_target}"),

            # 7. Exact CSS Selector (if provided)
            ("css_selector", clean_target),

            # 8. XPath Fallback
            ("xpath_button", f"xpath=//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{clean_target.lower()}')]"),
            ("xpath_input", f"xpath=//input[@name='{clean_target}' or @id='{clean_target}' or contains(@placeholder, '{clean_target}')]"),
            ("xpath_text", f"xpath=//*[contains(text(), '{clean_target}')]")
        ]

        for strategy_name, selector in strategies:
            try:
                locator = page.locator(selector).first
                count = await locator.count()
                if count > 0:
                    is_vis = await locator.is_visible(timeout=300)
                    if is_vis:
                        return locator, {
                            "resolved": True,
                            "resolved_by": strategy_name,
                            "selector_used": selector,
                            "target": target
                        }
            except Exception:
                continue

        # Fallback check: if element exists even if animating or not yet visible
        for strategy_name, selector in strategies[:8]:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    return locator, {
                        "resolved": True,
                        "resolved_by": f"{strategy_name}_fallback",
                        "selector_used": selector,
                        "target": target
                    }
            except Exception:
                continue

        return None, {
            "resolved": False,
            "target": target,
            "error": f"Element '{target}' could not be resolved by any of the 9 locator tiers."
        }
