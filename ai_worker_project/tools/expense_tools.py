from typing import Dict, Any
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from workhub_project.services.expense_service import ExpenseService

service = ExpenseService()

class GetAllExpensesTool(Tool):
    name = "get_all_expenses"
    description = "Retrieve expenses with optional filtering (by employee_id, status, query) and limit (default 10)."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword in expense notes/descriptions"},
            "employee_id": {"type": "string", "description": "Filter by employee ID"},
            "status": {"type": "string", "description": "Filter by expense status"},
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

class GetExpenseTool(Tool):
    name = "get_expense"
    description = "Retrieve a specific expense by ID."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    
    async def execute(self, id: str, **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data=service.get_by_id(id))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CreateExpenseTool(Tool):
    name = "create_expense"
    description = "Create a new expense."
    risk_level = RiskLevel.MEDIUM
    effect = "write"
    parameters = {"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]}
    
    async def execute(self, data: Dict[str, Any], **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data=service.create(data))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class UpdateExpenseTool(Tool):
    name = "update_expense"
    description = "Update an existing expense."
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

class DeleteExpenseTool(Tool):
    name = "delete_expense"
    description = "Delete a expense."
    risk_level = RiskLevel.HIGH
    effect = "write"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    
    async def execute(self, id: str, **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data={"success": service.delete(id)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
