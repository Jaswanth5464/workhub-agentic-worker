import logging
import json
from datetime import datetime
from ai_worker_project.tools.base import Tool, ToolResult, RiskLevel

logger = logging.getLogger(__name__)

from workhub_project.database.db_utils import _read_mock_db, _write_mock_db

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
            db = _read_mock_db()
            if "emails" not in db:
                db["emails"] = []
                
            new_msg = {
                "id": f"MSG-{str(len(db['emails']) + 1).zfill(3)}",
                "from_email": to_email,
                "subject": subject,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "read": 0,
                "body": body
            }
            db["emails"].insert(0, new_msg)
            _write_mock_db(db)
            
            return ToolResult(
                success=True, 
                data={
                    "status": "Email sent successfully and recorded in system",
                    "to": to_email,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class SearchEmployeeRecordsTool(Tool):
    name = "search_employee_db"
    description = (
        "Directly searches the internal employee database by name or ID without using the browser UI. "
        "Returns the raw employee JSON record."
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
        # We can read the mockData.js file and parse it to simulate a DB lookup
        try:
            import re
            with open("workhub_hr_app/mockData.js", "r", encoding="utf-8") as f:
                content = f.read()
            
            # Very hacky mock data extraction for demo purposes
            match = re.search(r"employees:\s*(\[.*?\]),?\s*\n\s*expenses", content, re.DOTALL)
            if not match:
                return ToolResult(success=False, error="Could not parse mock database.")
                
            # Clean up the JS to be valid JSON
            json_str = match.group(1).replace("'", '"')
            json_str = re.sub(r'(\w+):', r'"\1":', json_str) # quote keys
            
            try:
                employees = json.loads(json_str)
                results = [e for e in employees if query.lower() in e.get("name", "").lower() or query.lower() in e.get("id", "").lower()]
                return ToolResult(success=True, data={"results": results})
            except Exception as parse_e:
                return ToolResult(success=False, error=f"Failed to query database: {parse_e}")
                
        except Exception as e:
            return ToolResult(success=False, error=f"Database connection error: {str(e)}")
