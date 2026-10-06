import sqlite3
import os
import json

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workhub_project", "database", "company_database.sqlite"))

class IndependentVerifier:
    """
    Phase 2: Independent Verifier.
    Compares pre-action and post-action DB states via SELECT queries to prevent false successes.
    """
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.pre_state = self._snapshot()

    def _snapshot(self):
        if not os.path.exists(DB_PATH):
            return {}
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        snapshot = {}
        for table in ["employees", "expenses", "tasks", "leaves", "documents", "emails", "benefits", "audit_logs"]:
            try:
                c = conn.cursor()
                c.execute(f"SELECT * FROM {table}")
                snapshot[table] = [dict(row) for row in c.fetchall()]
            except:
                snapshot[table] = []
        conn.close()
        return snapshot

    def verify(self, task_description: str, final_answer: str) -> dict:
        post_state = self._snapshot()
        
        mutations = []
        for table, pre_rows in self.pre_state.items():
            if table == "audit_logs": continue
            post_rows = post_state.get(table, [])
            # Simple list equality check (assumes row order hasn't changed or isn't relevant for simple CRUD)
            if len(pre_rows) != len(post_rows) or pre_rows != post_rows:
                mutations.append(table)
                
        # Analyze if it was supposed to mutate
        import re
        lower_task = task_description.lower()
        mutating_keywords = ["delete", "remove", "update", "change", "add", "create", "pay", "approve", "reject", "terminate"]
        # Use regex to match whole words only to prevent substring bugs (like 'add' in 'address')
        expected_mutation = any(re.search(rf'\b{kw}\b', lower_task) for kw in mutating_keywords)
        
        status = "success"
        expected = "Task completed as requested."
        actual = f"Task completed without database mutations."

        if expected_mutation:
            if not mutations:
                status = "failed"
                expected = "Database state to reflect the requested changes."
                actual = "Database state remained completely unchanged. This is a false-success (hallucination)."
            else:
                status = "success"
                expected = "Database state to reflect the requested changes."
                actual = f"Verified structural database mutations in tables: {', '.join(mutations)}."
        else:
            if mutations:
                status = "failed"
                expected = "No database state changes."
                actual = f"Unsafe write detected! Unexpected mutations in tables: {', '.join(mutations)}."
                
        return {
            "status": status,
            "expected": expected,
            "actual": actual
        }
