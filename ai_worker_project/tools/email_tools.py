from typing import Dict, Any
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from workhub_project.services.email_service import EmailService

service = EmailService()

class GetAllEmailsTool(Tool):
    name = "get_all_emails"
    description = "Retrieve emails with optional filtering (by recipient, subject, query) and limit (default 10)."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword in subject or body"},
            "recipient": {"type": "string", "description": "Filter by recipient email"},
            "limit": {"type": "integer", "description": "Max records to return (default 10)"}
        }
    }
    
    async def execute(self, query: str = None, recipient: str = None, limit: int = 10, **kwargs) -> ToolResult:
        try:
            filters = {}
            if recipient: filters["recipient"] = recipient
            if query:
                return ToolResult(success=True, data=service.search(query=query, filters=filters, limit=limit))
            return ToolResult(success=True, data=service.get_all(limit=limit, filters=filters))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class GetEmailTool(Tool):
    name = "get_email"
    description = "Retrieve a specific email by ID."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    
    async def execute(self, id: str, **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data=service.get_by_id(id))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CreateEmailTool(Tool):
    name = "create_email"
    description = "Create a new email."
    risk_level = RiskLevel.MEDIUM
    effect = "write"
    parameters = {"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]}
    
    async def execute(self, data: Dict[str, Any], **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data=service.create(data))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class UpdateEmailTool(Tool):
    name = "update_email"
    description = "Update an existing email."
    risk_level = RiskLevel.HIGH
    effect = "write"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}, "data": {"type": "object"}}, "required": ["id", "data"]}
    
    async def execute(self, id: str, data: Dict[str, Any], **kwargs) -> ToolResult:
        try:
            existing = service.get_by_id(id)
            if not existing: return ToolResult(success=False, error="Not found")
            existing.update(data)
            return ToolResult(success=True, data=service.update(id, existing))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class DeleteEmailTool(Tool):
    name = "delete_email"
    description = "Delete a email."
    risk_level = RiskLevel.HIGH
    effect = "write"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    
    async def execute(self, id: str, **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data={"success": service.delete(id)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
