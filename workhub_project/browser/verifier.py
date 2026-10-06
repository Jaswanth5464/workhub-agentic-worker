"""
Dual-Layer Action Verifier (Browser UI State + SQLite Database Backend Validation).
"""

import sqlite3
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page
from .element_resolver import ElementResolver

logger = logging.getLogger(__name__)

class ActionVerifier:
    DB_PATH = "workhub_project/database/company_database.sqlite"

    @classmethod
    async def verify(
        cls,
        page: Page,
        action_name: str,
        ui_target: Optional[str] = None,
        expected_ui_text: Optional[str] = None,
        db_query: Optional[str] = None,
        db_expected_val: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Dual-layer verification:
        1. Checks Browser DOM state (e.g. status changed, notification appeared, row updated)
        2. Queries real SQLite database to confirm persistent entity state mutation.
        """
        # --- Layer 1: Browser UI Verification ---
        ui_ok = True
        ui_evidence = "UI verification bypassed (no target specified)."
        if ui_target and expected_ui_text:
            loc, _ = await ElementResolver.resolve(ui_target, page)
            if loc:
                actual_text = await loc.inner_text()
                ui_ok = (expected_ui_text.lower() in actual_text.lower())
                ui_evidence = f"UI matched expected text '{expected_ui_text}' in '{ui_target}' (Actual: '{actual_text[:60]}')."
            else:
                # Fallback: check whole page body
                body_text = await page.inner_text("body")
                ui_ok = (expected_ui_text.lower() in body_text.lower())
                ui_evidence = f"Page body contains '{expected_ui_text}': {ui_ok}"

        # --- Layer 2: Real Database Verification ---
        db_ok = True
        db_evidence = "Database verification bypassed (no query specified)."
        if db_query:
            try:
                conn = sqlite3.connect(cls.DB_PATH)
                cur = conn.cursor()
                cur.execute(db_query)
                rows = cur.fetchall()
                conn.close()

                if db_expected_val is not None:
                    db_ok = any(str(db_expected_val).lower() in str(r).lower() for r in rows)
                    db_evidence = f"DB query returned {len(rows)} rows. Target value '{db_expected_val}' found: {db_ok}."
                else:
                    db_ok = len(rows) > 0
                    db_evidence = f"DB query returned {len(rows)} matching records (Query: '{db_query[:80]}')."
            except Exception as e:
                db_ok = False
                db_evidence = f"DB verification query failed: {str(e)}"

        overall_verified = ui_ok and db_ok

        return {
            "action": action_name,
            "success": overall_verified,
            "verified": overall_verified,
            "ui_verified": ui_ok,
            "ui_evidence": ui_evidence,
            "db_verified": db_ok,
            "db_evidence": db_evidence
        }
