from ai_worker_project.tools.registry import ToolRegistry
from ai_worker_project.tools.sql_tool import SQLQueryTool
from ai_worker_project.tools.memory import MemorySaveTool, MemoryRecallTool
from ai_worker_project.tools.browser import BrowserTool

# Import all 35 CRUD tools
from ai_worker_project.tools.employee_tools import GetAllEmployeesTool, GetEmployeeTool, CreateEmployeeTool, UpdateEmployeeTool, DeleteEmployeeTool
from ai_worker_project.tools.expense_tools import GetAllExpensesTool, GetExpenseTool, CreateExpenseTool, UpdateExpenseTool, DeleteExpenseTool
from ai_worker_project.tools.task_tools import GetAllTasksTool, GetTaskTool, CreateTaskTool, UpdateTaskTool, DeleteTaskTool
from ai_worker_project.tools.leave_tools import GetAllLeavesTool, GetLeaveTool, CreateLeaveTool, UpdateLeaveTool, DeleteLeaveTool
from ai_worker_project.tools.document_tools import GetAllDocumentsTool, GetDocumentTool, CreateDocumentTool, UpdateDocumentTool, DeleteDocumentTool
from ai_worker_project.tools.email_tools import GetAllEmailsTool, GetEmailTool, CreateEmailTool, UpdateEmailTool, DeleteEmailTool
from ai_worker_project.tools.benefit_tools import GetAllBenefitsTool, GetBenefitTool, CreateBenefitTool, UpdateBenefitTool, DeleteBenefitTool

from ai_worker_project.tools.hr_tools import SendHREmailTool, SearchEmployeeRecordsTool
from ai_worker_project.tools.hr_extra_tools import (
    DownloadDocumentTool, UploadDocumentTool, GenerateReportTool,
    ScheduleInterviewTool, ApprovePayrollTool, OnboardEmployeeTool,
    OffboardEmployeeTool, IssueWarningTool, ManageBenefitsTool, FetchCompanyHolidaysTool
)

def get_default_registry() -> ToolRegistry:
    """Instantiate a registry and populate it with all allowed tools."""
    registry = ToolRegistry()
    
    # Generic tools
    registry.register(SQLQueryTool())
    registry.register(MemorySaveTool())
    registry.register(MemoryRecallTool())
    registry.register(BrowserTool())
    
    # The 35 HR Tools!
    # Employees
    registry.register(GetAllEmployeesTool())
    registry.register(GetEmployeeTool())
    registry.register(CreateEmployeeTool())
    registry.register(UpdateEmployeeTool())
    registry.register(DeleteEmployeeTool())
    
    # Expenses
    registry.register(GetAllExpensesTool())
    registry.register(GetExpenseTool())
    registry.register(CreateExpenseTool())
    registry.register(UpdateExpenseTool())
    registry.register(DeleteExpenseTool())
    
    # Tasks
    registry.register(GetAllTasksTool())
    registry.register(GetTaskTool())
    registry.register(CreateTaskTool())
    registry.register(UpdateTaskTool())
    registry.register(DeleteTaskTool())
    
    # Leaves
    registry.register(GetAllLeavesTool())
    registry.register(GetLeaveTool())
    registry.register(CreateLeaveTool())
    registry.register(UpdateLeaveTool())
    registry.register(DeleteLeaveTool())
    
    # Documents
    registry.register(GetAllDocumentsTool())
    registry.register(GetDocumentTool())
    registry.register(CreateDocumentTool())
    registry.register(UpdateDocumentTool())
    registry.register(DeleteDocumentTool())
    
    # Emails
    registry.register(GetAllEmailsTool())
    registry.register(GetEmailTool())
    registry.register(CreateEmailTool())
    registry.register(UpdateEmailTool())
    registry.register(DeleteEmailTool())
    
    # Benefits
    registry.register(GetAllBenefitsTool())
    registry.register(GetBenefitTool())
    registry.register(CreateBenefitTool())
    registry.register(UpdateBenefitTool())
    registry.register(DeleteBenefitTool())
    
    # Extra Convenience HR Tools
    registry.register(SendHREmailTool())
    registry.register(SearchEmployeeRecordsTool())
    registry.register(DownloadDocumentTool())
    registry.register(UploadDocumentTool())
    registry.register(GenerateReportTool())
    registry.register(ScheduleInterviewTool())
    registry.register(ApprovePayrollTool())
    registry.register(OnboardEmployeeTool())
    registry.register(OffboardEmployeeTool())
    registry.register(IssueWarningTool())
    registry.register(ManageBenefitsTool())
    registry.register(FetchCompanyHolidaysTool())
    
    return registry
