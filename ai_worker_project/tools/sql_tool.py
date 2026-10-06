"""
SQL Database Tool.

Allows the agent to execute SELECT and modifying queries (UPDATE, INSERT, DELETE) 
on the internal company database. Modifying queries require human approval.
"""
import sqlite3
import os
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel

class SQLQueryTool(Tool):
    name = "sql_query"
    description = (
        "Executes a raw SQL query against the internal SQLite company database. "
        "Available tables: "
        "1. employees (id, name, department, role, status, email, joined, emergencyContact, phone, manager) "
        "2. expenses (id, employee, date, amount, category, description, status, receiptId) "
        "3. tasks (id, title, assignedTo, dueDate, priority, status) "
        "4. leaves (id, employee, type, dates, status) "
        "5. documents (id, type, name, relatedTo, content) "
        "6. emails (id, from_email, subject, date, read, body) "
        "7. benefits (id, name, provider, coverage, enrolled, status). "
        "Read operations (SELECT) are safe. Mutating operations (UPDATE, INSERT, DELETE) require human approval."
    )
    # The base risk level is LOW (for SELECTs), but we will upgrade to MEDIUM dynamically
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The raw SQL query to execute (e.g., 'SELECT * FROM invoices' or 'UPDATE invoices SET status=\"PAID\"')."
            }
        },
        "required": ["query"]
    }
    
    def is_schema_alteration(self, query: str) -> bool:
        """Check if query attempts to alter schema or restructure tables/columns."""
        import re
        q = query.strip().upper()
        patterns = [
            r"\bALTER\s+TABLE\b",
            r"\bDROP\s+TABLE\b",
            r"\bDROP\s+COLUMN\b",
            r"\bADD\s+COLUMN\b",
            r"\bRENAME\s+TO\b",
            r"\bRENAME\s+COLUMN\b",
            r"\bALTER\b",
            r"\bDROP\b",
            r"\bTRUNCATE\b",
        ]
        return any(re.search(p, q) for p in patterns)

    def is_data_mutation(self, query: str) -> bool:
        """Check if query performs data modification (INSERT, UPDATE, DELETE, REPLACE)."""
        import re
        q = query.strip().upper()
        return bool(re.search(r"\b(UPDATE|INSERT|DELETE|REPLACE)\b", q))

    def requires_approval(self, args: dict) -> bool:
        """Dynamically require approval if the query is mutating."""
        query = args.get("query", "")
        return self.is_data_mutation(query)

    async def execute(self, query: str, **kwargs) -> ToolResult:
        query_upper = query.strip().upper()
        
        # 1. Hard Guardrail: Auto-reject schema restructuring / column changes
        if self.is_schema_alteration(query):
            return ToolResult(
                success=False,
                error=(
                    "Security Policy Violation: Auto-rejected. Table restructuring and column alterations "
                    "(ALTER, DROP, RENAME, ADD/DROP COLUMN) are strictly forbidden because restructuring the "
                    "database schema is not permitted. Only data-level operations (INSERT, UPDATE, DELETE) "
                    "are allowed with human approval."
                )
            )

        is_mutating = self.is_data_mutation(query)
        approval_granted = kwargs.get("approval_granted", False)
            
        db_path = os.path.join(os.path.dirname(__file__), "..", "..", "workhub_project", "database", "company_database.sqlite")
        db_path = os.path.abspath(db_path)
        if not os.path.exists(db_path):
            return ToolResult(success=False, error="Database file not found.")
            
        try:
            # Phase 4: Strict Read-Only Enforcement
            # Open with mode=ro unless this is an approved mutating query
            if is_mutating and approval_granted:
                conn = sqlite3.connect(db_path)
            else:
                db_uri = f"file:{db_path}?mode=ro"
                conn = sqlite3.connect(db_uri, uri=True)
                
            conn.row_factory = sqlite3.Row
            try:
                c = conn.cursor()
                c.execute(query)
                
                if is_mutating:
                    if not approval_granted:
                        return ToolResult(success=False, error="Safety violation: Mutating queries require human approval.")
                    conn.commit()
                    rows_affected = c.rowcount
                    return ToolResult(success=True, data={"message": f"Successfully executed. Rows affected: {rows_affected}"})
                else:
                    rows = c.fetchall()
                    results = [dict(row) for row in rows]
                    
                    if not results:
                        return ToolResult(success=True, data={"message": "Query executed successfully, but returned 0 rows."})
                        
                    return ToolResult(success=True, data=results)
            finally:
                conn.close()
            
        except sqlite3.Error as e:
            return ToolResult(success=False, error=f"SQL Execution Error: {e}")
        except Exception as e:
            return ToolResult(success=False, error=f"Unexpected Error: {e}")

