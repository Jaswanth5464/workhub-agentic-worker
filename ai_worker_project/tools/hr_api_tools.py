import logging
import json
import re
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel

logger = logging.getLogger(__name__)

from workhub_project.database.db_utils import _read_mock_db, _write_mock_db

class ManageExpenseTool(Tool):
    name = "manage_expense"
    description = "Approves or rejects a pending employee expense."
    risk_level = RiskLevel.HIGH # Requires approval because it's a financial action
    
    parameters = {
        "type": "object",
        "properties": {
            "expense_id": {"type": "string"},
            "action": {"type": "string", "enum": ["approve", "reject"]}
        },
        "required": ["expense_id", "action"]
    }
    
    async def execute(self, expense_id: str, action: str, **kwargs) -> ToolResult:
        try:
            db = _read_mock_db()
            expense = next((e for e in db["expenses"] if e["id"] == expense_id), None)
            if not expense:
                return ToolResult(success=False, error="Expense not found")
            
            expense["status"] = action + "d" if action.endswith("e") else action + "ed"
            _write_mock_db(db)
            
            return ToolResult(success=True, data={"status": f"Expense {action}d successfully."})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class ManageLeaveRequestTool(Tool):
    name = "manage_leave"
    description = "Approves or rejects a pending employee leave request."
    risk_level = RiskLevel.HIGH
    effect = "write"
    
    parameters = {
        "type": "object",
        "properties": {
            "leave_id": {"type": "string"},
            "action": {"type": "string", "enum": ["approve", "reject", "cancel"]}
        },
        "required": ["leave_id", "action"]
    }
    
    async def execute(self, leave_id: str, action: str, **kwargs) -> ToolResult:
        try:
            db = _read_mock_db()
            leave = next((l for l in db.get("leaves", []) if l["id"] == leave_id), None)
            if not leave:
                return ToolResult(success=False, error="Leave request not found")
            
            leave["status"] = "cancelled" if action == "cancel" else (action + "d" if action.endswith("e") else action + "ed")
            _write_mock_db(db)
            
            return ToolResult(success=True, data={"status": f"Leave {leave_id} {action}d successfully."})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class HRTaskManagementTool(Tool):
    name = "manage_hr_task"
    description = "Creates a new HR task or updates the status of an existing task."
    risk_level = RiskLevel.HIGH
    effect = "write"
    
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Optional. The ID of the task to update."},
            "title": {"type": "string", "description": "Optional. Title for a new task."},
            "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"], "description": "New status for the task."},
            "assignedTo": {"type": "string", "description": "Employee ID or Department Head to assign task to."}
        },
        "required": []
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        try:
            db = _read_mock_db()
            task_id = kwargs.get("task_id")
            title = kwargs.get("title")
            status = kwargs.get("status")
            assigned_to = kwargs.get("assignedTo") or kwargs.get("assigned_to")
            
            if task_id:
                task = next((t for t in db.get("tasks", []) if t["id"] == task_id), None)
                if not task:
                    return ToolResult(success=False, error="Task not found")
                if status:
                    task["status"] = status
                if title:
                    task["title"] = title
                if assigned_to:
                    task["assignedTo"] = assigned_to
            else:
                new_task = {
                    "id": f"TSK-{len(db.get('tasks', [])) + 100}",
                    "title": title or "New HR Task",
                    "status": status or "pending",
                    "assignedTo": assigned_to or "Admin",
                    "dueDate": "2026-10-30",
                    "priority": "medium"
                }
                if "tasks" not in db:
                    db["tasks"] = []
                db["tasks"].append(new_task)
                
            _write_mock_db(db)
            return ToolResult(success=True, data={"status": "Task updated successfully."})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class UpdateEmployeeProfileTool(Tool):
    name = "update_employee_profile"
    description = "Updates an employee's profile information (e.g. emergency contact, phone, status, role)."
    risk_level = RiskLevel.HIGH
    effect = "write"
    
    parameters = {
        "type": "object",
        "properties": {
            "employee_id": {"type": "string"},
            "emergency_contact": {"type": "string"},
            "phone": {"type": "string"},
            "status": {"type": "string", "description": "Employee status (active, inactive, terminated)"}
        },
        "required": ["employee_id"]
    }
    
    async def execute(self, employee_id: str, **kwargs) -> ToolResult:
        try:
            db = _read_mock_db()
            employee = next((e for e in db.get("employees", []) if e["id"] == employee_id), None)
            if not employee:
                return ToolResult(success=False, error="Employee not found")
            
            if "emergency_contact" in kwargs:
                employee["emergencyContact"] = kwargs["emergency_contact"]
            if "phone" in kwargs:
                employee["phone"] = kwargs["phone"]
            if "status" in kwargs:
                employee["status"] = kwargs["status"]
                
            _write_mock_db(db)
            return ToolResult(success=True, data={"status": f"Employee {employee_id} profile updated successfully."})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

