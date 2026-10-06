"""
Session Persistence, Checkpointing, and Idempotency Protection Manager.
"""

import os
import json
import time
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SessionManager:
    CHECKPOINT_DIR = Path("runs/browser_checkpoints")
    DB_PATH = "workhub_project/database/company_database.sqlite"

    def __init__(self):
        self.CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        session_id: str,
        task_id: str,
        subgoal: str,
        current_url: str,
        completed_actions: list,
        entity_ids: Optional[Dict[str, Any]] = None
    ) -> str:
        """Saves session execution state to a persistent JSON checkpoint."""
        filepath = self.CHECKPOINT_DIR / f"session_{session_id}.json"
        data = {
            "session_id": session_id,
            "task_id": task_id,
            "subgoal": subgoal,
            "current_url": current_url,
            "completed_actions": completed_actions,
            "entity_ids": entity_ids or {},
            "timestamp": time.time()
        }
        filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return str(filepath.resolve())

    def load_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Loads persistent session state if it exists."""
        filepath = self.CHECKPOINT_DIR / f"session_{session_id}.json"
        if filepath.exists():
            try:
                return json.loads(filepath.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def check_operation_status(self, entity_table: str, record_id: str) -> Dict[str, Any]:
        """
        Idempotency Protection:
        Inspects whether a mutation was already applied in the SQLite database before attempting a blind retry.
        """
        try:
            conn = sqlite3.connect(self.DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {entity_table} WHERE id = ?;", (record_id,))
            row = cur.fetchone()
            conn.close()

            if row:
                d = dict(row)
                return {
                    "exists": True,
                    "record_id": record_id,
                    "status": d.get("status", "found"),
                    "data": d
                }
            return {"exists": False, "record_id": record_id}
        except Exception as e:
            return {"exists": False, "error": str(e)}
