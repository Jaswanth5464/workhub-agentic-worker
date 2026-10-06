"""
Generic Data Tools: Enables the LLM to filter, sort, and aggregate stored results.
This prevents the LLM from hallucinating on truncated lists or doing math itself.
"""
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from typing import Dict, Any, Optional
from decimal import Decimal
from config.loader import settings as _cfg

_SQL_MAX_ROWS = _cfg.get("tools", {}).get("sql_max_rows", 100)

# We need a reference to the active ResultStore. 
# This can be set by the Orchestrator or Loop during execution.
class DataSelectTool(Tool):
    name = "data_select"
    description = "Filter, sort and pick rows from a stored result."
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "ref_id": {"type": "string", "description": "The result reference ID (e.g., r1)"},
            "filters": {"type": "object", "description": "Key-value pairs to filter by exactly"},
            "order_by": {"type": "string", "description": "Field to sort by"},
            "direction": {"type": "string", "enum": ["asc", "desc"], "default": "asc"},
            "limit": {"type": "integer", "default": 5}
        },
        "required": ["ref_id"]
    }
    
    # Needs to be injected
    result_store = None
    
    async def execute(self, ref_id: str, filters: dict = None, order_by: str = None, direction: str = "asc", limit: int = 5, **kwargs) -> ToolResult:
        if not self.result_store:
            return ToolResult(success=False, error="ResultStore not bound")
            
        data = self.result_store.get(ref_id)
        if not data:
            return ToolResult(success=False, error=f"Reference {ref_id} not found")
            
        if not isinstance(data, list):
            return ToolResult(success=False, error=f"Reference {ref_id} is not a list")
            
        # 1. Filter
        if filters:
            filtered = []
            for row in data:
                if isinstance(row, dict):
                    match = True
                    for k, v in filters.items():
                        if str(row.get(k)) != str(v):
                            match = False
                            break
                    if match:
                        filtered.append(row)
            data = filtered
            
        # 2. Sort
        if order_by:
            def get_sort_key(item):
                val = item.get(order_by)
                if val is None:
                    return ""
                # Attempt to parse as float for correct numeric sorting
                if isinstance(val, str):
                    clean_val = val.replace(',', '').replace('₹', '').replace('$', '').strip()
                    try:
                        return float(clean_val)
                    except ValueError:
                        return val
                return val
                
            data = sorted(data, key=lambda x: get_sort_key(x) if isinstance(x, dict) else "", reverse=(direction == "desc"))
            
        # 3. Limit
        res = data[:limit]
        return ToolResult(success=True, data=res)


class DataAggregateTool(Tool):
    name = "data_aggregate"
    description = "Aggregate a stored result (count, sum, min, max, avg)."
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "ref_id": {"type": "string", "description": "The result reference ID (e.g., r1)"},
            "op": {"type": "string", "enum": ["count", "sum", "min", "max", "avg"]},
            "field": {"type": "string", "description": "The field to aggregate (optional for count)"},
        },
        "required": ["ref_id", "op"]
    }
    
    result_store = None
    
    async def execute(self, ref_id: str, op: str, field: str = None, **kwargs) -> ToolResult:
        if not self.result_store:
            return ToolResult(success=False, error="ResultStore not bound")
            
        data = self.result_store.get(ref_id)
        if not data:
            return ToolResult(success=False, error=f"Reference {ref_id} not found")
            
        if not isinstance(data, list):
            return ToolResult(success=False, error=f"Reference {ref_id} is not a list")
            
        if op == "count":
            return ToolResult(success=True, data={"count": len(data)})
            
        if not field:
            return ToolResult(success=False, error="field is required for sum, min, max, avg")
            
        values = []
        for row in data:
            if isinstance(row, dict) and field in row:
                val = row[field]
                if isinstance(val, str):
                    clean_val = val.replace(',', '').replace('₹', '').replace('$', '').strip()
                    try:
                        values.append(Decimal(clean_val))
                    except:
                        pass
                elif isinstance(val, (int, float)):
                    values.append(Decimal(str(val)))
                    
        if not values:
            return ToolResult(success=False, error=f"No valid numeric values found in field {field}")
            
        if op == "sum":
            ans = sum(values)
        elif op == "min":
            ans = min(values)
        elif op == "max":
            ans = max(values)
        elif op == "avg":
            ans = sum(values) / len(values)
            
        return ToolResult(success=True, data={op: float(ans)})


class DataQueryTool(Tool):
    name = "data_query"
    description = (
        "Run a read-only SQL SELECT query against the internal database. "
        "Use this for custom aggregations or data questions not covered by specific tools."
    )
    effect = "read"
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "A valid SQLite SELECT query."}
        },
        "required": ["query"]
    }
    
    def get_schema(self) -> Dict[str, Any]:
        schema = super().get_schema()
        import sqlite3, os
        db_path = os.path.join(os.path.dirname(__file__), "..", "environment", "internal_db", "internal_db.db")
        if os.path.exists(db_path):
            try:
                db_uri_path = db_path.replace('\\', '/')
                conn = sqlite3.connect(f"file:{db_uri_path}?mode=ro", uri=True, timeout=1.0)
                cursor = conn.cursor()
                cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                schema_text = "Live Schema:\n"
                for name, sql in tables:
                    if name != 'sqlite_sequence':
                        schema_text += f"- {name}: {sql}\n"
                conn.close()
                schema["description"] += f"\n\n{schema_text}"
            except Exception as e:
                schema["description"] += f"\n\n(Could not fetch live schema: {e})"
        return schema
        
    async def execute(self, query: str, **kwargs) -> ToolResult:
        import re, sqlite3, os
        stripped = query.strip()

        if not stripped.upper().startswith("SELECT"):
            return ToolResult(success=False, error="Only SELECT queries are allowed.")
        if ";" in stripped.rstrip(";"):
            return ToolResult(success=False, error="Multiple statements are not allowed.")

        blocked_patterns = [
            r"\bUNION\b", r"\bDROP\b", r"\bDELETE\b", r"\bINSERT\b", r"\bUPDATE\b", r"\bALTER\b",
            r"sqlite_master", r"sqlite_temp_master", r"--", r"/\*.*?\*/"
        ]
        for pattern in blocked_patterns:
            if re.search(pattern, stripped, re.IGNORECASE | re.DOTALL):
                return ToolResult(success=False, error=f"Query blocked: Pattern '{pattern}' not allowed.")

        db_path = os.path.join(os.path.dirname(__file__), "..", "environment", "internal_db", "internal_db.db")
        if not os.path.exists(db_path):
            return ToolResult(success=False, error="Database does not exist yet.")

        db_uri_path = db_path.replace('\\', '/')
        uri = f"file:{db_uri_path}?mode=ro"
        
        def authorizer(action_code, tname, cname, sql_location, trigger_name):
            if action_code == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK
            if action_code == sqlite3.SQLITE_READ:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        try:
            conn = sqlite3.connect(uri, uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            conn.set_authorizer(authorizer)
            cursor = conn.cursor()
            cursor.execute("PRAGMA query_only = ON")
            cursor.execute(stripped)
            rows = [dict(row) for row in cursor.fetchmany(_SQL_MAX_ROWS)]
            conn.close()
            return ToolResult(success=True, data={"results": rows, "row_count": len(rows)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
