import logging
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from datetime import datetime
from workhub_project.services.document_service import DocumentService
from workhub_project.services.task_service import TaskService
from workhub_project.services.employee_service import EmployeeService
from workhub_project.services.benefit_service import BenefitService

logger = logging.getLogger(__name__)

doc_service = DocumentService()
task_service = TaskService()
emp_service = EmployeeService()
benefit_service = BenefitService()

class DownloadDocumentTool(Tool):
    name = "download_document"
    description = "Downloads a document (PDF, policy, etc.) from the HR system."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {"type": "object", "properties": {"document_id": {"type": "string"}}, "required": ["document_id"]}
    async def execute(self, document_id: str, **kwargs) -> ToolResult:
        doc = doc_service.get_by_id(document_id)
        if not doc:
            return ToolResult(success=False, error=f"Document {document_id} not found.")
        return ToolResult(success=True, data=doc)

class UploadDocumentTool(Tool):
    name = "upload_document"
    description = "Uploads a new document to the HR system."
    risk_level = RiskLevel.MEDIUM
    effect = "write"
    parameters = {
        "type": "object", 
        "properties": {
            "file_name": {"type": "string"},
            "content": {"type": "string", "description": "Optional content"}
        }, 
        "required": ["file_name"]
    }
    async def execute(self, file_name: str, content: str = "Uploaded document content.", **kwargs) -> ToolResult:
        try:
            created = doc_service.create({
                "type": "Policy" if "policy" in file_name.lower() else "General",
                "name": file_name,
                "relatedTo": "All",
                "content": content
            })
            return ToolResult(success=True, data=created)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class GenerateReportTool(Tool):
    name = "generate_report"
    description = "Generates an HR analytics report."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {"type": "object", "properties": {"report_type": {"type": "string"}}, "required": ["report_type"]}
    async def execute(self, report_type: str, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"status": f"Report '{report_type}' generated successfully."})

class ScheduleInterviewTool(Tool):
    name = "schedule_interview"
    description = "Schedules an interview for a candidate by creating a high-priority task."
    risk_level = RiskLevel.MEDIUM
    effect = "write"
    parameters = {"type": "object", "properties": {"candidate_name": {"type": "string"}, "date": {"type": "string"}}, "required": ["candidate_name"]}
    async def execute(self, candidate_name: str, date: str = None, **kwargs) -> ToolResult:
        try:
            task = task_service.create({
                "title": f"Interview with {candidate_name}",
                "assignedTo": "Admin",
                "dueDate": date or datetime.now().strftime("%Y-%m-%d"),
                "priority": "high",
                "status": "pending"
            })
            return ToolResult(success=True, data=task)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class ApprovePayrollTool(Tool):
    name = "approve_payroll"
    description = "Approves payroll for the current cycle."
    risk_level = RiskLevel.HIGH
    effect = "write"
    parameters = {"type": "object", "properties": {}, "required": []}
    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"status": "Payroll approved and funds disbursed."})

class OnboardEmployeeTool(Tool):
    name = "onboard_employee"
    description = "Initiates the onboarding sequence for a new hire and creates an active employee record."
    risk_level = RiskLevel.MEDIUM
    effect = "write"
    parameters = {"type": "object", "properties": {"employee_name": {"type": "string"}, "department": {"type": "string"}, "role": {"type": "string"}}, "required": ["employee_name"]}
    async def execute(self, employee_name: str, department: str = "Engineering", role: str = "New Hire", **kwargs) -> ToolResult:
        try:
            emp = emp_service.create({
                "name": employee_name,
                "department": department,
                "role": role,
                "status": "active",
                "email": f"{employee_name.lower().replace(' ', '.')}@workhub.local",
                "joined": datetime.now().strftime("%Y-%m-%d"),
                "emergencyContact": "Pending",
                "phone": "Pending",
                "manager": "Admin"
            })
            return ToolResult(success=True, data=emp)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class OffboardEmployeeTool(Tool):
    name = "offboard_employee"
    description = "Initiates offboarding sequence, setting employee status to inactive."
    risk_level = RiskLevel.HIGH
    effect = "write"
    parameters = {"type": "object", "properties": {"employee_id": {"type": "string"}}, "required": ["employee_id"]}
    async def execute(self, employee_id: str, **kwargs) -> ToolResult:
        try:
            emp = emp_service.get_by_id(employee_id)
            if not emp:
                return ToolResult(success=False, error=f"Employee {employee_id} not found")
            updated = emp_service.update(employee_id, {"status": "inactive"})
            return ToolResult(success=True, data=updated)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class IssueWarningTool(Tool):
    name = "issue_warning"
    description = "Issues a formal HR warning to an employee."
    risk_level = RiskLevel.LOW
    parameters = {"type": "object", "properties": {"employee_id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["employee_id"]}
    async def execute(self, employee_id: str, reason: str = "General policy notice", **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"status": f"Warning issued to {employee_id}. Reason: {reason}"})

class ManageBenefitsTool(Tool):
    name = "manage_benefits"
    description = "Updates benefit enrollment status."
    risk_level = RiskLevel.MEDIUM
    effect = "write"
    parameters = {"type": "object", "properties": {"benefit_id": {"type": "string"}, "status": {"type": "string"}}, "required": ["benefit_id"]}
    async def execute(self, benefit_id: str, status: str = None, **kwargs) -> ToolResult:
        try:
            ben = benefit_service.get_by_id(benefit_id)
            if not ben:
                return ToolResult(success=False, error=f"Benefit {benefit_id} not found")
            new_status = status or ("active" if ben.get("status") == "inactive" else "inactive")
            updated = benefit_service.update(benefit_id, {"status": new_status})
            return ToolResult(success=True, data=updated)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class FetchCompanyHolidaysTool(Tool):
    name = "fetch_holidays"
    description = "Fetches the company holiday calendar."
    risk_level = RiskLevel.LOW
    effect = "read"
    parameters = {"type": "object", "properties": {}, "required": []}
    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, data={"holidays": ["New Year's Day", "Republic Day", "Independence Day", "Diwali", "Christmas"]})
