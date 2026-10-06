from typing import Dict, Any
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from workhub_project.services.leave_service import LeaveService

service = LeaveService()

class GetAllLeavesTool(Tool):
    name = "get_all_leaves"
    description = "Retrieve leaves with optional filtering (by employee_id, status, query) and limit (default 10)."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword in leave reason"},
            "employee_id": {"type": "string", "description": "Filter by employee ID"},
            "status": {"type": "string", "description": "Filter by status (pending, approved, rejected)"},
            "limit": {"type": "integer", "description": "Max records to return (default 10)"}
        }
    }
    
    async def execute(self, query: str = None, employee_id: str = None, status: str = None, limit: int = 10, **kwargs) -> ToolResult:
        try:
            filters = {}
            if employee_id: filters["employee_id"] = employee_id
            if status: filters["status"] = status
            if query:
                return ToolResult(success=True, data=service.search(query=query, filters=filters, limit=limit))
            return ToolResult(success=True, data=service.get_all(limit=limit, filters=filters))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class GetLeaveTool(Tool):
    name = "get_leave"
    description = "Retrieve a specific leave by ID."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    
    async def execute(self, id: str, **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data=service.get_by_id(id))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CreateLeaveTool(Tool):
    name = "create_leave"
    description = "Create a new leave."
    risk_level = RiskLevel.MEDIUM
    effect = "write"
    parameters = {"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]}
    
    async def execute(self, data: Dict[str, Any], **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data=service.create(data))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class UpdateLeaveTool(Tool):
    name = "update_leave"
    description = "Update an existing leave."
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

class DeleteLeaveTool(Tool):
    name = "delete_leave"
    description = "Delete a leave."
    risk_level = RiskLevel.HIGH
    effect = "write"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    
    async def execute(self, id: str, **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data={"success": service.delete(id)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
