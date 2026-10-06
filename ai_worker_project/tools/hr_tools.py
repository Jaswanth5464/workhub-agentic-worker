import logging
from datetime import datetime
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel
from workhub_project.services.employee_service import EmployeeService
from workhub_project.services.email_service import EmailService

logger = logging.getLogger(__name__)

class SendHREmailTool(Tool):
    name = "send_email"
    description = (
        "Sends an email to an employee or admin regarding HR tasks, leave approvals, or general communication."
    )
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "to_email": {
                "type": "string",
                "description": "The recipient's email address."
            },
            "subject": {
                "type": "string",
                "description": "The subject of the email."
            },
            "body": {
                "type": "string",
                "description": "The body content of the email."
            }
        },
        "required": ["to_email", "subject", "body"]
    }
    
    async def execute(self, to_email: str, subject: str, body: str, **kwargs) -> ToolResult:
        logger.info(f"Sending email to {to_email} - Subject: {subject}")
        try:
            email_service = EmailService()
            new_msg = {
                "from_email": to_email,
                "subject": subject,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "read": 0,
                "body": body
            }
            res = email_service.create(new_msg)
            return ToolResult(
                success=True, 
                data={
                    "status": "Email sent successfully and recorded in SQLite database",
                    "record": res,
                    "to": to_email,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class SearchEmployeeRecordsTool(Tool):
    name = "search_employee_db"
    description = (
        "Directly searches the internal employee SQLite database by name or ID. "
        "Returns matching employee records."
    )
    risk_level = RiskLevel.LOW
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The name or employee ID to search for."
            }
        },
        "required": ["query"]
    }
    
    async def execute(self, query: str, **kwargs) -> ToolResult:
        try:
            emp_service = EmployeeService()
            query_str = query.strip()
            # If query is an ID lookup
            emp = emp_service.get_by_id(query_str)
            if emp:
                return ToolResult(success=True, data={"results": [emp]})
            
            # Otherwise search by name or fields
            results = emp_service.search(query=query_str, limit=10)
            return ToolResult(success=True, data={"results": results})
        except Exception as e:
            return ToolResult(success=False, error=f"Database query error: {str(e)}")

