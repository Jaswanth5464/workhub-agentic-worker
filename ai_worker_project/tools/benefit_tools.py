from typing import Dict, Any
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from workhub_project.services.benefit_service import BenefitService

service = BenefitService()

class GetAllBenefitsTool(Tool):
    name = "get_all_benefits"
    description = "Retrieve benefits with optional filtering (by employee_id, benefit_type, query) and limit (default 10)."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword in plan_name or benefit_type"},
            "employee_id": {"type": "string", "description": "Filter by employee ID"},
            "benefit_type": {"type": "string", "description": "Filter by benefit type (health, dental, 401k, etc.)"},
            "limit": {"type": "integer", "description": "Max records to return (default 10)"}
        }
    }
    
    async def execute(self, query: str = None, employee_id: str = None, benefit_type: str = None, limit: int = 10, **kwargs) -> ToolResult:
        try:
            filters = {}
            if employee_id: filters["employee_id"] = employee_id
            if benefit_type: filters["benefit_type"] = benefit_type
            if query:
                return ToolResult(success=True, data=service.search(query=query, filters=filters, limit=limit))
            return ToolResult(success=True, data=service.get_all(limit=limit, filters=filters))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class GetBenefitTool(Tool):
    name = "get_benefit"
    description = "Retrieve a specific benefit by ID."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    
    async def execute(self, id: str, **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data=service.get_by_id(id))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class CreateBenefitTool(Tool):
    name = "create_benefit"
    description = "Create a new benefit."
    risk_level = RiskLevel.MEDIUM
    effect = "write"
    parameters = {"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]}
    
    async def execute(self, data: Dict[str, Any], **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data=service.create(data))
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class UpdateBenefitTool(Tool):
    name = "update_benefit"
    description = "Update an existing benefit."
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

class DeleteBenefitTool(Tool):
    name = "delete_benefit"
    description = "Delete a benefit."
    risk_level = RiskLevel.HIGH
    effect = "write"
    parameters = {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}
    
    async def execute(self, id: str, **kwargs) -> ToolResult:
        try:
            return ToolResult(success=True, data={"success": service.delete(id)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
