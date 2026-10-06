"""
Finance API Tool (Database).

Phase 2: Reads and writes payables to the InternalDB Database API.
Writing requires MEDIUM risk (Human Approval).
"""

import httpx
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from config.loader import settings as _cfg


class FinanceDatabaseTool(Tool):
    name = "finance_db"
    description = (
        "Interacts with the InternalDB Database API. "
        "Use action='read' to list payables. Use action='write' to create a new payable."
    )
    # Marked as MEDIUM because 'write' mutates state. The Registry will enforce approval.
    risk_level = RiskLevel.MEDIUM 
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write"],
                "description": "Whether to read existing payables or write a new one."
            },
            "payload": {
                "type": "object",
                "description": "Required when action='write'. Must contain entity, record_id, amount, currency, due_date.",
                "properties": {
                    "entity": {"type": "string"},
                    "record_id": {"type": "string"},
                    "amount": {"type": "number"},
                    "currency": {"type": "string"},
                    "due_date": {"type": "string"}
                }
            }
        },
        "required": ["action"]
    }
    
    def requires_approval(self, args: dict) -> bool:
        return args.get("action") == "write"
    
    async def execute(self, action: str, payload: dict = None, **kwargs) -> ToolResult:
        base_url = _cfg.get("services", {}).get("acmefinance_url")
        if not base_url:
            return ToolResult(success=False, error="acmefinance_url not configured in settings")
        base_url += "/api/payables"
        
        async with httpx.AsyncClient() as client:
            try:
                if action == "read":
                    resp = await client.get(base_url)
                    resp.raise_for_status()
                    return ToolResult(success=True, data=resp.json())
                    
                elif action == "write":
                    if not payload:
                        return ToolResult(success=False, error="Payload required for write action")
                    
                    resp = await client.post(base_url, json=payload)
                    
                    if resp.status_code == 409:
                        return ToolResult(success=False, error=f"Duplicate: {resp.json().get('detail')}")
                    elif resp.status_code == 400:
                        return ToolResult(success=False, error=f"Bad Request: {resp.json().get('detail')}")
                        
                    resp.raise_for_status()
                    return ToolResult(success=True, data=resp.json())
                else:
                    return ToolResult(success=False, error="Unknown action")
            except Exception as e:
                return ToolResult(success=False, error=f"Finance DB error: {str(e)}")
