"""
Entity API Tool.

Phase 2: Reads data from the internal EntityHub API.
URL is configured in config/settings.yaml → services.vendorhub_url
"""

import httpx
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from config.loader import settings as _cfg


class EntityAPITool(Tool):
    name = "api_tool"
    description = (
        "Fetches record metadata from the EntityHub API. "
        "Allows filtering by entity name."
    )
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "entity": {
                "type": "string",
                "description": "Optional entity name to filter by."
            },
            "record_id": {
                "type": "string",
                "description": "Optional specific record ID to fetch details."
            }
        },
        "required": []
    }
    
    async def execute(self, entity: str = None, record_id: str = None, **kwargs) -> ToolResult:
        base_url = _cfg.get("services", {}).get("vendorhub_url")
        if not base_url:
            return ToolResult(success=False, error="vendorhub_url not configured in settings")
        base_url += "/api/invoices"
        
        async with httpx.AsyncClient() as client:
            try:
                if record_id:
                    resp = await client.get(f"{base_url}/{record_id}")
                else:
                    params = {"vendor": entity} if entity else {}
                    resp = await client.get(base_url, params=params)
                    
                if resp.status_code == 404:
                    return ToolResult(success=False, error="Not found")
                resp.raise_for_status()
                return ToolResult(success=True, data=resp.json())
            except Exception as e:
                return ToolResult(success=False, error=f"API error: {str(e)}")
