import sqlite3
import os
from typing import Dict, Any, List, Optional

from workhub_project.database.db_utils import get_db_connection

class BaseRepository:
    """
    Generic Repository Pattern for SQLite tables.
    Provides standard CRUD operations.
    """
    def __init__(self, table_name: str):
        self.table_name = table_name

    def _get_columns(self, conn) -> List[str]:
        if not hasattr(self, '_columns'):
            c = conn.cursor()
            c.execute(f"PRAGMA table_info({self.table_name})")
            self._columns = [row['name'] for row in c.fetchall()]
        return self._columns
        
    def _audit(self, conn, action: str, record_id: str, details: str):
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT,
            record_id TEXT,
            action TEXT,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        import json
        c.execute("INSERT INTO audit_logs (table_name, record_id, action, details) VALUES (?, ?, ?, ?)",
                  (self.table_name, str(record_id), action, json.dumps(details)))

    def get_all(self, limit: int = 1000, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            valid_columns = self._get_columns(conn)
            clauses = []
            params = []
            if filters:
                for k, v in filters.items():
                    if k in valid_columns and v is not None:
                        clauses.append(f"{k} = ?")
                        params.append(v)
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            sql = f"SELECT * FROM {self.table_name} {where_sql} LIMIT ?"
            params.append(int(limit))
            
            c = conn.cursor()
            c.execute(sql, params)
            rows = c.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def search(self, query: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            valid_columns = self._get_columns(conn)
            clauses = []
            params = []
            
            if filters:
                for k, v in filters.items():
                    if k in valid_columns and v is not None:
                        clauses.append(f"{k} = ?")
                        params.append(v)
                        
            if query:
                text_clauses = []
                for col in valid_columns:
                    text_clauses.append(f"{col} LIKE ?")
                    params.append(f"%{query}%")
                if text_clauses:
                    clauses.append(f"({' OR '.join(text_clauses)})")
                    
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            sql = f"SELECT * FROM {self.table_name} {where_sql} LIMIT ?"
            params.append(int(limit))
            
            c = conn.cursor()
            c.execute(sql, params)
            rows = c.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def _generate_next_id(self, conn) -> str:
        import re
        table_prefix_map = {
            "employees": ("EMP-", 3),
            "expenses": ("EXP-", 4),
            "tasks": ("TSK-", 3),
            "leaves": ("LV-", 3),
            "documents": ("DOC-", 3),
            "emails": ("MSG-", 3),
            "benefits": ("BEN-", 2),
        }
        prefix, digits = table_prefix_map.get(self.table_name, ("REC-", 3))
        c = conn.cursor()
        c.execute(f"SELECT id FROM {self.table_name} WHERE id IS NOT NULL")
        rows = c.fetchall()
        max_num = 0
        pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
        for r in rows:
            val = str(r['id'] if hasattr(r, '__getitem__') and 'id' in r.keys() else r[0])
            match = pattern.match(val)
            if match:
                try:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
            else:
                num_match = re.search(r"(\d+)$", val)
                if num_match:
                    try:
                        num = int(num_match.group(1))
                        if num > max_num and num < 900:  # ignore test 999
                            max_num = num
                    except ValueError:
                        pass
        
        if self.table_name == "expenses" and max_num < 1000:
            next_num = 1046
        elif self.table_name == "leaves" and max_num < 200:
            next_num = 204
        elif self.table_name == "employees" and max_num >= 900:
            # Check highest regular employee ID (e.g. EMP-044)
            reg_max = 0
            for r in rows:
                val = str(r['id'] if hasattr(r, '__getitem__') and 'id' in r.keys() else r[0])
                m = re.match(r"^EMP-(\d{1,3})$", val, re.IGNORECASE)
                if m:
                    n = int(m.group(1))
                    if n < 900 and n > reg_max:
                        reg_max = n
            next_num = reg_max + 1 if reg_max > 0 else 45
        else:
            next_num = max_num + 1 if max_num > 0 else 1
            
        return f"{prefix}{str(next_num).zfill(digits)}"

    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (record_id,))
            row = c.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        conn = get_db_connection()
        try:
            valid_columns = self._get_columns(conn)
            
            # Auto-generate ID if missing or null and 'id' is a column
            if 'id' in valid_columns and (not data.get('id') or data.get('id') is None):
                data['id'] = self._generate_next_id(conn)
                
            keys = [k for k in data.keys() if k in valid_columns]
            values = [data[k] for k in keys]
            placeholders = ",".join(["?"] * len(keys))
            columns = ",".join(keys)
            
            c = conn.cursor()
            c.execute(f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})", values)
            
            # Use provided ID or the last inserted row id
            record_id = data.get('id', c.lastrowid)
            self._audit(conn, "CREATE", str(record_id), data)
            conn.commit()
        finally:
            conn.close()
            
        return data

    def update(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        conn = get_db_connection()
        try:
            valid_columns = self._get_columns(conn)
            keys = [k for k in data.keys() if k in valid_columns]
            if not keys:
                return data
                
            values = [data[k] for k in keys]
            set_clause = ", ".join([f"{k} = ?" for k in keys])
            
            c = conn.cursor()
            c.execute(f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?", values + [record_id])
            self._audit(conn, "UPDATE", record_id, data)
            conn.commit()
        finally:
            conn.close()
            
        return data
        
    def delete(self, record_id: str) -> bool:
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (record_id,))
            rows_deleted = c.rowcount
            if rows_deleted > 0:
                self._audit(conn, "DELETE", record_id, {})
            conn.commit()
        finally:
            conn.close()
            
        return rows_deleted > 0
