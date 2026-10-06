import sqlite3
import os
from typing import List, Dict, Any

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "company_database.sqlite"))

def get_db_connection() -> sqlite3.Connection:
    """Provides a fresh SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Ensures database tables and audit log tables exist."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT,
            record_id TEXT,
            action TEXT,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
    finally:
        conn.close()

def get_recent_audit_logs(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches recent audit log activities directly from SQLite."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        return [dict(row) for row in rows]
    except Exception:
        return []
    finally:
        conn.close()


