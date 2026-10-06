import logging
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from workhub_project.services.expense_service import ExpenseService
from workhub_project.services.leave_service import LeaveService
from workhub_project.services.task_service import TaskService
from workhub_project.services.employee_service import EmployeeService

logger = logging.getLogger(__name__)

expense_service = ExpenseService()
leave_service = LeaveService()
task_service = TaskService()
emp_service = EmployeeService()

class ManageExpenseTool(Tool):
    name = "manage_expense"
    description = "Approves or rejects a pending employee expense directly in SQLite."
    risk_level = RiskLevel.HIGH
    effect = "write"
    
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
            expense = expense_service.get_by_id(expense_id)
            if not expense:
                return ToolResult(success=False, error="Expense not found")
            
            new_status = action + "d" if action.endswith("e") else action + "ed"
            updated = expense_service.update(expense_id, {"status": new_status})
            return ToolResult(success=True, data={"status": f"Expense {action}d successfully.", "record": updated})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class ManageLeaveRequestTool(Tool):
    name = "manage_leave"
    description = "Approves or rejects a pending employee leave request directly in SQLite."
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
            leave = leave_service.get_by_id(leave_id)
            if not leave:
                return ToolResult(success=False, error="Leave request not found")
            
            new_status = "cancelled" if action == "cancel" else (action + "d" if action.endswith("e") else action + "ed")
            updated = leave_service.update(leave_id, {"status": new_status})
            return ToolResult(success=True, data={"status": f"Leave {leave_id} {action}d successfully.", "record": updated})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class ListAssignableEmployeesTool(Tool):
    name = "list_assignable_employees"
    description = "Lists all current active employees from SQLite with their ID, name, and department to easily select for task assignments, expense filing, or leave approvals."
    risk_level = RiskLevel.LOW
    effect = "read"
    
    parameters = {
        "type": "object",
        "properties": {
            "department": {"type": "string", "description": "Optional department filter"},
            "limit": {"type": "integer", "description": "Max employees to return (default 100)"}
        }
    }
    
    async def execute(self, department: str = None, limit: int = 100, **kwargs) -> ToolResult:
        try:
            filters = {"status": "active"}
            if department:
                filters["department"] = department
            employees = emp_service.get_all(limit=limit, filters=filters)
            formatted = [{
                "id": e["id"],
                "name": e["name"],
                "department": e.get("department", "General"),
                "role": e.get("role", "Staff"),
                "label": f"{e['name']} ({e['id']} - {e.get('department', 'General')})"
            } for e in employees]
            return ToolResult(success=True, data={"employees": formatted, "count": len(formatted)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class HRTaskManagementTool(Tool):
    name = "manage_hr_task"
    description = "Creates a new HR task or updates the status of an existing task directly in SQLite. You can assign tasks to any employee by Name (e.g., 'Jane Smith') or Employee ID (e.g., 'EMP-002') or 'Admin'."
    risk_level = RiskLevel.HIGH
    effect = "write"
    
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Optional. The ID of the task to update."},
            "title": {"type": "string", "description": "Optional. Title for a new task."},
            "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"], "description": "New status for the task."},
            "assignedTo": {"type": "string", "description": "Employee Name, Employee ID (e.g. EMP-002), or 'Admin' to assign task to."}
        },
        "required": []
    }
    
    async def execute(self, **kwargs) -> ToolResult:
        try:
            task_id = kwargs.get("task_id")
            title = kwargs.get("title")
            status = kwargs.get("status")
            assigned_to = kwargs.get("assignedTo") or kwargs.get("assigned_to")
            
            # Resolve assigned_to if employee ID is provided
            if assigned_to and assigned_to.upper().startswith("EMP-"):
                matched = emp_service.get_by_id(assigned_to)
                if matched:
                    assigned_to = matched["name"]

            if task_id:
                task = task_service.get_by_id(task_id)
                if not task:
                    return ToolResult(success=False, error="Task not found")
                update_fields = {}
                if status: update_fields["status"] = status
                if title: update_fields["title"] = title
                if assigned_to: update_fields["assignedTo"] = assigned_to
                updated = task_service.update(task_id, update_fields)
                return ToolResult(success=True, data={"status": "Task updated successfully.", "record": updated})
            else:
                new_task = task_service.create({
                    "title": title or "New HR Task",
                    "status": status or "pending",
                    "assignedTo": assigned_to or "Admin",
                    "dueDate": kwargs.get("due_date") or kwargs.get("dueDate") or "2026-10-30",
                    "priority": kwargs.get("priority") or "medium"
                })
                return ToolResult(success=True, data={"status": "Task created successfully.", "record": new_task})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class UpdateEmployeeProfileTool(Tool):
    name = "update_employee_profile"
    description = "Updates an employee's profile information directly in SQLite."
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
            employee = emp_service.get_by_id(employee_id)
            if not employee:
                return ToolResult(success=False, error="Employee not found")
            
            update_data = {}
            if "emergency_contact" in kwargs:
                update_data["emergencyContact"] = kwargs["emergency_contact"]
            if "phone" in kwargs:
                update_data["phone"] = kwargs["phone"]
            if "status" in kwargs:
                update_data["status"] = kwargs["status"]
                
            updated = emp_service.update(employee_id, update_data)
            return ToolResult(success=True, data={"status": f"Employee {employee_id} profile updated successfully.", "record": updated})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
