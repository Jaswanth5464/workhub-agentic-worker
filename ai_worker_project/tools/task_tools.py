from typing import Dict, Any
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from workhub_project.services.task_service import TaskService

service = TaskService()

class GetAllTasksTool(Tool):
    name = "get_all_tasks"
    description = "Retrieve tasks with optional filtering (by assigned_to, status, query) and limit (default 10)."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword in task title or description"},
            "assigned_to": {"type": "string", "description": "Filter by assigned employee ID"},
            "status": {"type": "string", "description": "Filter by status (pending, in_progress, completed)"},
            "limit": {"type": "integer", "description": "Max records to return (default 10)"}
        }
    }
    
    async def execute(self, query: str = None, assigned_to: str = None, status: str = None, limit: int = 10, **kwargs) -> ToolResult:
        try:
            filters = {}
            if assigned_to: filters["assigned_to"] = assigned_to
            if status: filters["status"] = status
            if query:
                return ToolResult(success=True, data=service.search(query=query, filters=filters, limit=limit))
            return ToolResult(success=True, data=service.get_all(limit=limit, filters=filters))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class GetTaskTool(Tool):
    name = "get_task"
    description = "Retrieve a specific task by ID."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    
    async def execute(self, id: str, **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data=service.get_by_id(id))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CreateTaskTool(Tool):
    name = "create_task"
    description = "Create a new task."
    risk_level = RiskLevel.MEDIUM
    effect = "write"
    parameters = {"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]}
    
    async def execute(self, data: Dict[str, Any], **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data=service.create(data))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class UpdateTaskTool(Tool):
    name = "update_task"
    description = "Update an existing task."
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

class DeleteTaskTool(Tool):
    name = "delete_task"
    description = "Delete a task."
    risk_level = RiskLevel.HIGH
    effect = "write"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    
    async def execute(self, id: str, **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data={"success": service.delete(id)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
