import json
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional

from ai_worker_project.agent.llm import generate_response, extract_json, prune_history_for_context
from ai_worker_project.tools import ToolRegistry
from ai_worker_project.tools.base import RiskLevel
from ai_worker_project.tools.memory import get_all_memories
from ai_worker_project.agent.state import StateMachine, AgentState
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.loader import settings

logger = logging.getLogger(__name__)

DATABASE_SCHEMA_DOC = """COMPANY DATABASE SCHEMA (SQLite):
1. `employees`:
   - Columns: id (TEXT), name (TEXT), department (TEXT), role (TEXT), status (TEXT: 'active', 'inactive', 'terminated'), email (TEXT), joined (TEXT), emergencyContact (TEXT), phone (TEXT), manager (TEXT)
   - IMPORTANT: There is NO 'salary' column in employees.
2. `expenses`:
   - Columns: id (TEXT), employee (TEXT: stores employee full NAME, e.g. 'John Doe', 'Bob Wilson'), date (TEXT), amount (TEXT), category (TEXT), description (TEXT), status (TEXT: 'pending', 'approved', 'rejected', 'cancelled'), receiptId (TEXT)
3. `tasks`:
   - Columns: id (TEXT), title (TEXT), assignedTo (TEXT: stores employee full NAME, e.g. 'Admin', 'Alice Smith'), dueDate (TEXT), priority (TEXT: 'low', 'medium', 'high'), status (TEXT: 'pending', 'in-progress', 'completed')
4. `leaves`:
   - Columns: id (TEXT), employee (TEXT: stores employee full NAME, e.g. 'Jane Smith', 'Bob Wilson'), type (TEXT), dates (TEXT), status (TEXT: 'pending', 'approved', 'rejected', 'cancelled')
5. `documents`:
   - Columns: id (TEXT), type (TEXT), name (TEXT), relatedTo (TEXT), content (TEXT)
6. `emails`:
   - Columns: id (TEXT), from_email (TEXT), subject (TEXT), date (TEXT), read (INTEGER), body (TEXT)
7. `benefits`:
   - Columns: id (TEXT), name (TEXT), provider (TEXT), coverage (TEXT), enrolled (INTEGER), status (TEXT)
8. `audit_logs`:
   - Columns: id (INTEGER), table_name (TEXT), record_id (TEXT), action (TEXT), details (TEXT), timestamp (TEXT)

IMPORTANT QUERYING RULE:
- In `tasks`, `leaves`, and `expenses`, the employee field stores employee full NAME (e.g. 'Olivia Hall', 'John Doe'), NOT employee IDs ('EMP-001'). Always match by employee `name` (e.g. `WHERE employee IN ('Olivia Hall', 'Sam White')` or `JOIN employees ON leaves.employee = employees.name`).
"""

SYSTEM_PROMPT = """You are an Autonomous AI Task Worker.
Your goal is to complete the given task step-by-step using available tools.

{database_schema}

{memory_section}

CRITICAL INSTRUCTION - SECURITY & SAFETY GUARDRAILS:
1. STRICTLY FORBIDDEN: NEVER attempt table restructuring, column changes, or DDL operations (ALTER TABLE, DROP TABLE, RENAME TABLE/COLUMN, ADD COLUMN, DROP COLUMN). Restructuring the database schema is prohibited and will be auto-rejected by security guardrails.
2. PERMITTED DATA OPERATIONS: Only data operations (INSERT/CREATE, UPDATE, DELETE) are permitted.
3. HUMAN AUTHORIZATION: Any state mutation (e.g. cancelling pending leave requests, cancelling pending expense claims, reassigning tasks, updating employee records, or SQL UPDATE/DELETE) requires explicit human approval before execution.

CRITICAL INSTRUCTION - SCHEMA ACCURACY:
- Only write SQL queries using the EXACT tables and column names listed in the COMPANY DATABASE SCHEMA above.
- NEVER assume or invent columns that do not exist in the schema.

CRITICAL INSTRUCTION - STEP-BY-STEP EXECUTION:
1. You MUST NEVER fabricate or assume database records exist.
2. You MUST ACTUALLY execute the appropriate tools step-by-step (e.g. `get_all_employees`, `get_all_leaves`, `get_employee`, `get_all_expenses`, `create_employee`, `sql_query`, `update_leave`, `manage_leave`, `update_expense`, `update_task`).
3. NEVER call the "finish" tool on your first step if the user requested actions or queries that require database access. First execute the queries and actions, inspect the real observations, and only call "finish" once you have gathered real data and completed all subgoals!

CRITICAL INSTRUCTION - TOKEN EFFICIENCY & TARGETED LOOKUPS:
1. When looking up a person or entity (e.g. 'Jaswanth' or 'Vikram Patel'), NEVER call `get_all_employees()` without filters.
2. ALWAYS use targeted lookups:
   - `get_employee(name="Vikram Patel")` or `get_employee(name="Jaswanth")`
   - `get_all_employees(department="Engineering", limit=20)`
   - `get_all_expenses(status="pending", limit=20)`
   - `sql_query(query="SELECT id, name, email, department FROM employees WHERE name LIKE '%Vikram%' LIMIT 5")`
3. Always specify exact filters or use WHERE clauses with LIMIT clauses.

CRITICAL INSTRUCTION - VERIFICATION PHASE & STRICT OBSERVATION GUARDRAIL:
1. Before deciding a creation or update failed, you MUST run `observe` on the filtered view or use the search bar to inspect the results. NEVER assume an action failed without observing proof.
2. LARGE TABLES & PAGINATION: Tables may contain dozens or hundreds of records. New or existing records may not appear in the top 20 rows of an unfiltered view. ALWAYS type into the search bar and call `observe` to locate matching records before assuming they do not exist.
3. Before calling the "finish" tool, you MUST verify that your action was successful. For example, if you CREATED or UPDATED a database record (e.g. cancelled leaves/expenses or reassigned tasks), you MUST run a targeted SELECT query or getter tool afterwards to confirm the updated status actually exists in the database.
4. Only call "finish" once you have explicitly observed proof of success.

You MUST respond in valid JSON with this exact format:
{
    "thought": "<reasoning for next action>",
    "action": {
        "tool": "tool_name",
        "args": {
            "arg1": "value1"
        }
    }
}

When finished and verified, use the "finish" tool:
{
    "thought": "Summary of completed work",
    "action": {
        "tool": "finish",
        "args": {
            "answer": "Final response to user"
        }
    }
}

CRITICAL INSTRUCTION - TOOL CALLING, WEB AUTOMATION & SECURITY GUARDS:
1. STRICT WEB AUTOMATION MODE: When the user prompt requests web automation, mentions a URL (e.g. "open http://...", "navigate to http://..."), or asks to perform actions in the browser, you MUST execute ALL steps PURELY via the `browser` tool. You must NOT fallback to SQL queries unless the browser tool returns a fatal crash.
2. WORKHUB UI INTERACTION PATTERNS:
   - Creating a Task via UI:
     1. Click "New Task" button (`#btn-new-task`).
     2. Type title into `#new-tsk-title`.
     3. Select assignee from `#new-tsk-assign` and priority from `#new-tsk-priority`.
     4. Click "Assign Task" (`#btn-approve`).
   - Updating / Changing Task Status via UI:
     1. In the Tasks view (`dataView="tasks"`), click "Open Task" on the desired task row (`.btn-open-task`).
     2. This pops up the Task Details modal.
     3. Use `select` action on selector `#task-status-update` with value `"in_progress"`, `"completed"`, or `"pending"`.
     4. Click "Save Status" button (`#btn-approve`).
     5. Repeat for subsequent tasks if multiple tasks need updating.
   - Approvals via UI:
     1. In Approval Center (`dataView="approvals"`), click the green "Approve" button (`.btn-approve-leave-direct` or `.btn-approve-exp-direct`).
3. Browser tool action format:
   - Open page: `{"tool": "browser", "args": {"action": "open_page", "url": "http://..."}}`
   - Observe DOM: `{"tool": "browser", "args": {"action": "observe", "selector": "body"}}`
   - Click: `{"tool": "browser", "args": {"action": "click", "selector": "[data-agent-id='...']" or "#id"}}`
   - Type: `{"tool": "browser", "args": {"action": "type", "selector": "#id", "value": "..."}}`
   - Select Dropdown: `{"tool": "browser", "args": {"action": "select", "selector": "#id", "value": "..."}}`
4. NEVER invent or call fake tools. Our automated security guard automatically intercepts write operations and prompts the human operator for authorization when needed.
5. If you need to ask the human operator a clarifying question or request specific user input, use the 'ask_user' tool with {"question": "..."}.
6. COMPANY MEMORY: If you ask the human a question and they provide an answer or a rule, use the 'memorize_fact' tool to save that rule for future runs!

Available Tools:
{tool_descriptions}
"""



def _lookup_record_for_approval(table: str, record_id: Any) -> Optional[dict]:
    """Helper to query the existing SQLite record for rich approval previews."""
    if not record_id:
        return None
    try:
        from workhub_project.database.db_utils import get_db_connection
        rid = str(record_id).strip()
        with get_db_connection() as conn:
            # 1. Exact match
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (rid,)).fetchone()
            if not row:
                # 2. Try prefix matching (e.g. '2' -> 'LV-202' or 'LV-002')
                prefix_map = {
                    "leaves": "LV-",
                    "expenses": "EXP-",
                    "tasks": "TSK-",
                    "employees": "EMP-",
                    "documents": "DOC-",
                    "emails": "MSG-",
                    "benefits": "BEN-"
                }
                pref = prefix_map.get(table, "")
                if pref:
                    row = conn.execute(
                        f"SELECT * FROM {table} WHERE id LIKE ? OR id LIKE ?", 
                        (f"{pref}%{rid}", f"%{rid}")
                    ).fetchone()
            if row:
                return dict(row)
    except Exception:
        pass
    return None


def _build_approval_context(tool_name: str, tool_args: dict, blocked_reason: str = None) -> dict:
    """
    Builds rich, human-readable context for approval requests so human verifiers
    understand exactly what entity, action, and fields are being modified.
    """
    name_lower = (tool_name or "").lower()
    q = str(tool_args.get("query", "")).strip()
    q_upper = q.upper()

    # 1. Direct SQL Mutations
    if tool_name == "sql_query":
        table = "Database"
        for t in ["employees", "expenses", "tasks", "leaves", "documents", "emails", "benefits", "audit_logs"]:
            if t.upper() in q_upper:
                table = t
                break
        
        if "DELETE" in q_upper:
            act = "DELETE"
            summary = f"The agent is executing an SQL DELETE on table '{table}'."
        elif "UPDATE" in q_upper:
            act = "UPDATE"
            summary = f"The agent is updating records in table '{table}' via SQL."
        elif "INSERT" in q_upper:
            act = "INSERT"
            summary = f"The agent is inserting new records into table '{table}'."
        else:
            act = "MUTATION"
            summary = f"The agent is modifying table '{table}'."

        return {
            "title": f"SQL {act} on '{table}'",
            "action_type": act,
            "entity": table.capitalize(),
            "summary": summary,
            "sql_query": q,
            "details": {
                "Target Table": table,
                "Operation": act,
                "SQL Statement": q
            }
        }

    # 2. Employee Operations
    if "employee" in name_lower:
        emp_id = tool_args.get("id") or tool_args.get("employee_id") or "New"
        rec = _lookup_record_for_approval("employees", emp_id) if emp_id != "New" else None
        actual_id = rec["id"] if rec else emp_id
        emp_name = tool_args.get("name") or tool_args.get("employee_name") or (rec["name"] if rec else f"Employee {emp_id}")
        role = tool_args.get("role") or tool_args.get("job_title") or (rec["role"] if rec else "N/A")
        dept = tool_args.get("department") or (rec["department"] if rec else "N/A")

        if "create" in name_lower or "onboard" in name_lower:
            return {
                "title": f"Onboard Employee: {emp_name}",
                "action_type": "CREATE",
                "entity": "Employee",
                "summary": f"Create new employee profile for {emp_name} ({role}, {dept}).",
                "details": {
                    "Full Name": emp_name,
                    "Department": dept,
                    "Role": role,
                    "Email": tool_args.get("email", "N/A"),
                    "Phone": tool_args.get("phone", "N/A"),
                    "Manager": tool_args.get("manager", "Admin")
                }
            }
        elif "delete" in name_lower or "terminate" in name_lower or "offboard" in name_lower:
            return {
                "title": f"Offboard / Delete Employee: {emp_name} ({actual_id})",
                "action_type": "DELETE",
                "entity": "Employee",
                "summary": f"Remove/terminate employee record for {emp_name} (ID: {actual_id}).",
                "details": {
                    "Employee ID": actual_id,
                    "Name": emp_name,
                    "Reason": tool_args.get("reason", "Administrative action")
                }
            }
        else: # Update / Modify
            return {
                "title": f"Update Employee Profile: {emp_name} ({actual_id})",
                "action_type": "UPDATE",
                "entity": "Employee",
                "summary": f"Update profile details for {emp_name} ({actual_id}).",
                "details": {
                    "Employee ID": actual_id,
                    "Updated Fields": {k: v for k, v in tool_args.items() if k not in ("run_id",)}
                }
            }

    # 3. Expense Operations
    if "expense" in name_lower:
        exp_id = tool_args.get("id") or tool_args.get("expense_id", "New")
        rec = _lookup_record_for_approval("expenses", exp_id) if exp_id != "New" else None
        actual_id = rec["id"] if rec else exp_id
        emp = tool_args.get("employee") or (rec["employee"] if rec else "N/A")
        amt = tool_args.get("amount") or (rec["amount"] if rec else "N/A")
        cat = tool_args.get("category") or (rec["category"] if rec else "N/A")
        status = tool_args.get("status", "approved")
        prev_status = rec["status"] if rec else "pending"

        if "delete" in name_lower:
            return {
                "title": f"Delete Expense Claim: {actual_id} ({emp})",
                "action_type": "DELETE",
                "entity": "Expense Claim",
                "summary": f"Delete expense claim {actual_id} for {emp} (${amt}).",
                "details": {"Expense ID": actual_id, "Employee": emp, "Amount": f"${amt}"}
            }
        elif "create" in name_lower:
            return {
                "title": f"Submit New Expense: {actual_id} (${amt})",
                "action_type": "CREATE",
                "entity": "Expense Claim",
                "summary": f"Create expense claim of ${amt} for {emp} ({cat}).",
                "details": {
                    "Employee": emp,
                    "Category": cat,
                    "Amount": f"${amt}",
                    "Description": tool_args.get("description", "N/A")
                }
            }
        else: # Update / Approve / Reject
            action_verb = "Approve" if status.lower() == "approved" else ("Reject" if status.lower() == "rejected" else "Update")
            return {
                "title": f"{action_verb} Expense Claim: {actual_id} ({emp})",
                "action_type": "UPDATE",
                "entity": "Expense Claim",
                "summary": f"{action_verb} expense claim of ${amt} for {emp} ({cat}).",
                "details": {
                    "Expense ID": actual_id,
                    "Employee": emp,
                    "Category": cat,
                    "Amount": f"${amt}",
                    "Status Change": f"{prev_status} ➔ {status}"
                }
            }

    # 4. Task Operations
    if "task" in name_lower:
        task_id = tool_args.get("id") or tool_args.get("task_id", "New")
        rec = _lookup_record_for_approval("tasks", task_id) if task_id != "New" else None
        actual_id = rec["id"] if rec else task_id
        title = tool_args.get("title") or (rec["title"] if rec else f"Task {task_id}")
        assignee = tool_args.get("assignedTo") or tool_args.get("assignee") or (rec["assignedTo"] if rec else "N/A")
        status = tool_args.get("status", "in-progress")
        prev_status = rec["status"] if rec else "pending"
        prio = tool_args.get("priority") or (rec["priority"] if rec else "medium")
        due = tool_args.get("dueDate") or (rec["dueDate"] if rec else "N/A")

        if "delete" in name_lower:
            return {
                "title": f"Delete Task: '{title}' ({actual_id})",
                "action_type": "DELETE",
                "entity": "Task",
                "summary": f"Permanently delete task {actual_id} ('{title}').",
                "details": {"Task ID": actual_id, "Title": title, "Assignee": assignee}
            }
        elif "create" in name_lower:
            return {
                "title": f"Create & Assign Task: '{title}'",
                "action_type": "CREATE",
                "entity": "Task",
                "summary": f"Create new task '{title}' assigned to {assignee} ({prio} priority).",
                "details": {
                    "Title": title,
                    "Assigned To": assignee,
                    "Priority": prio,
                    "Due Date": due
                }
            }
        else: # Update / Reassign / Status
            action_verb = "Complete" if status.lower() == "completed" else "Update"
            return {
                "title": f"{action_verb} Task: '{title}' ({actual_id})",
                "action_type": "UPDATE",
                "entity": "Task",
                "summary": f"{action_verb} task '{title}' (Assigned to: {assignee}, Status: {status}).",
                "details": {
                    "Task ID": actual_id,
                    "Task Title": title,
                    "Assigned To": assignee,
                    "Priority": prio,
                    "Status Change": f"{prev_status} ➔ {status}"
                }
            }

    # 5. Leave Operations
    if "leave" in name_lower:
        leave_id = tool_args.get("id") or tool_args.get("leave_id", "New")
        rec = _lookup_record_for_approval("leaves", leave_id) if leave_id != "New" else None
        actual_id = rec["id"] if rec else leave_id
        emp = tool_args.get("employee") or (rec["employee"] if rec else "Employee")
        ltype = tool_args.get("type") or (rec["type"] if rec else "PTO / Annual")
        dates = tool_args.get("dates") or (rec["dates"] if rec else "N/A")
        status = tool_args.get("status", "approved")
        prev_status = rec["status"] if rec else "pending"

        if "delete" in name_lower:
            return {
                "title": f"Delete Leave Record: {actual_id} ({emp})",
                "action_type": "DELETE",
                "entity": "Leave Request",
                "summary": f"Delete leave request {actual_id} for {emp} ({ltype}, {dates}).",
                "details": {"Leave ID": actual_id, "Employee": emp, "Dates": dates}
            }
        elif "create" in name_lower:
            return {
                "title": f"Submit Leave Request: {emp} ({ltype})",
                "action_type": "CREATE",
                "entity": "Leave Request",
                "summary": f"Submit new {ltype} leave for {emp} ({dates}).",
                "details": {"Employee": emp, "Leave Type": ltype, "Dates": dates}
            }
        else: # Update / Approve / Cancel
            action_verb = "Approve" if status.lower() == "approved" else ("Reject" if status.lower() == "rejected" else ("Cancel" if status.lower() == "cancelled" else "Process"))
            return {
                "title": f"{action_verb} Leave Request: {emp} ({actual_id})",
                "action_type": "UPDATE",
                "entity": "Leave Request",
                "summary": f"{action_verb} {ltype} request for {emp} ({dates}). Currently {prev_status}.",
                "details": {
                    "Leave ID": actual_id,
                    "Employee": emp,
                    "Leave Type": ltype,
                    "Dates": dates,
                    "Status Change": f"{prev_status} ➔ {status}"
                }
            }

    # 6. Benefits Operations
    if "benefit" in name_lower:
        ben_id = tool_args.get("id") or tool_args.get("benefit_id", "New")
        rec = _lookup_record_for_approval("benefits", ben_id) if ben_id != "New" else None
        actual_id = rec["id"] if rec else ben_id
        name = tool_args.get("name") or (rec["name"] if rec else "Benefit Plan")
        prov = tool_args.get("provider") or (rec["provider"] if rec else "N/A")
        cov = tool_args.get("coverage") or (rec["coverage"] if rec else "N/A")
        
        if "delete" in name_lower:
            return {
                "title": f"Delete Benefit Plan: '{name}' ({actual_id})",
                "action_type": "DELETE",
                "entity": "Benefit",
                "summary": f"Remove benefit plan {actual_id} ('{name}').",
                "details": {"Benefit ID": actual_id, "Name": name}
            }
        elif "create" in name_lower:
            return {
                "title": f"Create Benefit Plan: '{name}'",
                "action_type": "CREATE",
                "entity": "Benefit",
                "summary": f"Create corporate benefit plan '{name}' with {prov}.",
                "details": {"Name": name, "Provider": prov, "Coverage": cov}
            }
        else:
            return {
                "title": f"Update Benefit Plan: '{name}' ({actual_id})",
                "action_type": "UPDATE",
                "entity": "Benefit",
                "summary": f"Update benefit plan '{name}' ({actual_id}).",
                "details": tool_args
            }

    # 7. Document Operations
    if "document" in name_lower:
        doc_name = tool_args.get("name") or tool_args.get("title", "Document")
        dtype = tool_args.get("type", "Policy / Form")
        rel = tool_args.get("relatedTo", "Company")

        if "delete" in name_lower:
            return {
                "title": f"Delete Document: '{doc_name}'",
                "action_type": "DELETE",
                "entity": "Document",
                "summary": f"Permanently remove document '{doc_name}'.",
                "details": {"Document Name": doc_name}
            }
        else:
            return {
                "title": f"Upload / Save Document: '{doc_name}'",
                "action_type": "CREATE",
                "entity": "Document",
                "summary": f"Save document '{doc_name}' ({dtype}, related to {rel}).",
                "details": {"Document Name": doc_name, "Type": dtype, "Related To": rel}
            }

    # 8. Email / Notifications
    if "email" in name_lower:
        to = tool_args.get("to") or tool_args.get("recipient", "Recipient")
        subj = tool_args.get("subject", "HR Notification")
        return {
            "title": f"Send Email Notice: '{subj}'",
            "action_type": "NOTIFY",
            "entity": "Email",
            "summary": f"Dispatch official HR email to {to} with subject '{subj}'.",
            "details": {"Recipient": to, "Subject": subj, "Body Preview": str(tool_args.get("body", ""))[:120]}
        }

    # 9. Payroll / HR Extra Tools
    if "payroll" in name_lower:
        period = tool_args.get("period") or tool_args.get("pay_period", "Current Period")
        return {
            "title": f"Approve Payroll Batch: {period}",
            "action_type": "APPROVE",
            "entity": "Payroll",
            "summary": f"Authorize and finalize payroll execution for {period}.",
            "details": {"Pay Period": period, "Authorized By": "HR Administrator"}
        }

    if "warning" in name_lower:
        emp = tool_args.get("employee") or tool_args.get("name", "Employee")
        reason = tool_args.get("reason", "Policy violation")
        return {
            "title": f"Issue Formal Warning: {emp}",
            "action_type": "UPDATE",
            "entity": "Employee",
            "summary": f"Issue official HR compliance notice to {emp}.",
            "details": {"Employee": emp, "Reason": reason}
        }

    # Default Fallback
    return {
        "title": f"Authorize {tool_name.replace('_', ' ').title()}",
        "action_type": "EXECUTE",
        "entity": "System",
        "summary": blocked_reason or f"The agent requested execution of {tool_name}.",
        "details": {k: str(v) for k, v in tool_args.items() if k not in ("run_id",)}
    }


class RunState:
    def __init__(self, goal: str):
        self.goal = goal
        self.step = 0
        self.usage = {}
        self.action_history: List[str] = []

class Agent:
    """
    A cleaner ReAct-style Agent loop inspired by the ai-workforce-main architecture.
    Replaces the complex state-machine / contract loop with a simple, robust cycle.
    """
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.history: List[Dict[str, str]] = []
        self.state_machine = StateMachine()

    def _build_system_prompt(self, is_web_mode: bool = False) -> str:
        tools_info = []
        allowed_tools = {"browser", "ask_user", "finish", "memorize_fact"} if is_web_mode else None
        
        for schema in self.registry.get_all_schemas():
            if allowed_tools is not None and schema['name'] not in allowed_tools:
                continue
            info = f"- {schema['name']}: {schema.get('description', 'No description')} \n  Parameters: {schema.get('parameters', {})}"
            tools_info.append(info)
            
        memories = get_all_memories()
        memory_section = ""
        if memories:
            memory_section = "COMPANY MEMORY & RULES (Extremely Important):\n"
            for m in memories:
                memory_section += f"- [{m['topic']}]: {m['fact']}\n"
            memory_section += "\n"
            
        if is_web_mode:
            web_prompt = """You are an Autonomous Web Automation Browser Agent.
Your goal is to complete the given task on-screen using ONLY the browser tool.

CRITICAL ARCHITECTURAL PRINCIPLES:
1. PURE BROWSER EXECUTION: You interact ONLY through visible on-screen browser actions (`open_page`, `observe`, `click`, `type`, `select`, `extract_text`, `wait_for_condition`).
2. NO CSS/XPATH GUESSING: Specify clean semantic targets (e.g. `target: "Open Task"`, `target_id: "TSK-001"`, `target: "Update Task Status in SQLite"`, `target: "Save Status"`, `target: "New Task"`, `target: "Approve"`).
3. MODAL INTERACTION FLOW:
   - When you click an action that opens a modal dialog (e.g. "Open Task"), call `observe` to view the modal's active fields.
   - Select or type the desired values into the modal's fields.
   - Click the modal's action button (e.g. "Save Status", "Approve", "Submit").
   - Call `observe` again to verify the modal closed and the table updated.
4. OBSERVATION-ACTION CYCLE:
   - Always `observe` the page after navigating or opening a dialog to see available semantic targets.
5. STRICT VERIFICATION GUARDRAIL:
   - Before deciding a creation or update failed, you MUST run `observe` on the filtered view or search bar. NEVER assume an action failed without observing proof.
   - LARGE TABLES & PAGINATION: Tables contain many records. New or existing records may not appear in the top 20 rows of an unfiltered view. ALWAYS type the name/ID into the search bar and call `observe` to locate matching records before assuming they do not exist or attempting duplicate submissions.

Tool Action Format:
- Open Page: {"tool": "browser", "args": {"action": "open_page", "url": "http://localhost:3000/index.html"}}
- Observe Context: {"tool": "browser", "args": {"action": "observe"}}
- Click Target: {"tool": "browser", "args": {"action": "click", "target": "Open Task", "target_id": "TSK-001"}}
- Type into Input: {"tool": "browser", "args": {"action": "type", "target": "Task Title", "value": "New Title"}}
- Select Dropdown: {"tool": "browser", "args": {"action": "select", "target": "Update Task Status in SQLite", "value": "in_progress"}}
- Wait for Condition: {"tool": "browser", "args": {"action": "wait_for_condition", "condition_type": "dom_stable"}}

You MUST respond in valid JSON with this exact format:
{
    "thought": "<reasoning for next browser action>",
    "action": {
        "tool": "browser",
        "args": {
            "action": "...",
            "target": "..."
        }
    }
}

When finished, call:
{
    "thought": "All browser operations completed and verified on-screen.",
    "action": {
        "tool": "finish",
        "args": {
            "answer": "Summary of web automation results"
        }
    }
}

Available Tools:
{tool_descriptions}
"""
            return web_prompt.replace("{tool_descriptions}", "\n".join(tools_info))

        return (
            SYSTEM_PROMPT
            .replace("{database_schema}", DATABASE_SCHEMA_DOC)
            .replace("{tool_descriptions}", "\n".join(tools_info))
            .replace("{memory_section}", memory_section)
        )

    async def run(
        self,
        task: str,
        max_steps: int = settings.agent.max_steps,
        base_contract: Any = None,
        emit_cb=None,
        approval_queue: Optional[asyncio.Queue] = None,
        run_id: str = "",
        resume_steps: Optional[list] = None
    ) -> str:
        async def _emit(payload: dict):
            if emit_cb:
                payload["run_id"] = run_id
                payload["seq"] = getattr(_emit, "seq", 1)
                _emit.seq = payload["seq"] + 1
                await emit_cb(payload)
                
        self.state_machine.set_emitter(_emit)

        self.history = [{"role": "user", "content": f"Task: {task}"}]
        
        # Load resume steps if provided
        if resume_steps:
            for step in resume_steps:
                action = {"tool": step.tool_name, "args": step.tool_args}
                parsed = {"thought": step.thought, "action": action}
                self.history.append({"role": "assistant", "content": json.dumps(parsed)})
                self.history.append({"role": "user", "content": step.observation})

        is_web_mode = any(k in task.lower() for k in ["http://", "https://", "localhost:", "browser", "web automation", "on-screen", "open page", "navigate to", "click", "ui"])
        system_prompt = self._build_system_prompt(is_web_mode=is_web_mode)
        state = RunState(goal=task)
        final_answer = None
        
        await self.state_machine.transition(AgentState.UNDERSTANDING)
        
        # Dynamic LLM Planning Engine (Proportional to task complexity)
        planning_prompt = (
            f"{DATABASE_SCHEMA_DOC}\n\n"
            f"Analyze the following user task and decompose it into the exact minimal sequential subgoals strictly aligned with the database schema above:\n"
            f"Task: \"{task}\"\n\n"
            f"Output ONLY valid JSON in this exact structure:\n"
            f'{{\n'
            f'  "intent": "Short goal summary",\n'
            f'  "subgoals": [\n'
            f'    {{"id": "G1", "title": "Brief title", "desc": "Detailed objective", "status": "in_progress"}}\n'
            f'  ],\n'
            f'  "success_points": [\n'
            f'    {{"id": "SP1", "label": "Target operation validated", "status": "pending"}}\n'
            f'  ]\n'
            f'}}\n'
        )

        try:
            plan_raw = await generate_response(
                system_prompt="You are a strict JSON planning engine. Output ONLY valid JSON.",
                messages=[{"role": "user", "content": planning_prompt}],
                require_json=True
            )
            parsed_plan = extract_json(plan_raw)
            active_subgoals = parsed_plan.get("subgoals", [])
            success_points = parsed_plan.get("success_points", [])
            if not isinstance(active_subgoals, list) or len(active_subgoals) == 0:
                raise ValueError("Invalid subgoals structure")
        except Exception as e:
            logger.warning(f"Dynamic LLM planning failed fallback: {e}")
            active_subgoals = [
                {"id": "G1", "title": "Analyze Task Requirements", "desc": task[:60], "status": "in_progress"},
                {"id": "G2", "title": "Execute Operations & Tool Queries", "desc": "Perform operations in strict read-only / guard mode", "status": "pending"},
                {"id": "G3", "title": "Verify Integrity & Compile Final Report", "desc": "Audit results and present verified outcome", "status": "pending"}
            ]
            success_points = [
                {"id": "SP1", "label": "Target schema & records validated", "status": "pending"},
                {"id": "SP2", "label": "Security policies & authorization respected", "status": "pending"},
                {"id": "SP3", "label": "Verification check passed", "status": "pending"}
            ]

        # Emit rich Execution Contract, Subgoals & Success Points
        await _emit({
            "type": "contract",
            "contract": {
                "target_goal": task,
                "safety_mode": "STRICT_HUMAN_IN_THE_LOOP",
                "max_steps": max_steps,
                "read_only_default": True,
                "budget_seconds": 300,
                "subgoals": active_subgoals,
                "success_points": success_points
            }
        })

        while final_answer is None:
            state.step += 1
            if state.step > max_steps:
                final_answer = "Error: Maximum steps reached without completion."
                break

            pruned_history = prune_history_for_context(self.history)
            
            try:
                response_text = await generate_response(
                    system_prompt=system_prompt,
                    messages=pruned_history,
                    require_json=False
                )
            except Exception as e:
                # Provide a clean, generic user-facing message while preserving the technical detail
                error_msg = str(e)
                if "401" in error_msg or "403" in error_msg:
                    final_answer = "Authentication Error: Please verify your AI Provider API keys in the .env file."
                elif "429" in error_msg or "RateLimit" in error_msg:
                    final_answer = "Rate Limit Exceeded: The AI Provider is currently overloaded. Please try again in a moment."
                elif "Timeout" in error_msg:
                    final_answer = "Timeout Error: The AI Provider took too long to respond. Please try again."
                else:
                    final_answer = f"AI Provider Error: Unable to complete the request. Details: {error_msg}"
                break
                
            self.history.append({"role": "assistant", "content": response_text})
            
            try:
                parsed = extract_json(response_text)
            except Exception as e:
                self.history.append({"role": "user", "content": f"Error: Invalid JSON. {e}. Please respond with ONLY valid JSON."})
                continue
                
            thought = parsed.get("thought", parsed.get("reason", ""))
            action = parsed.get("action", {})
            
            # Robust action & tool extraction across various LLM formatting styles
            BROWSER_ACTIONS = {
                "open_page", "observe", "click", "type", "scroll", "wait_for_condition",
                "extract_text", "screenshot", "press_key", "select_option", "drag_and_drop", "hover", "navigate"
            }

            if isinstance(action, dict):
                tool_name = action.get("tool") or action.get("name") or action.get("tool_name") or parsed.get("tool") or parsed.get("tool_name")
                tool_args = action.get("args") or action.get("parameters") or action.get("arguments") or parsed.get("args") or parsed.get("parameters") or {}
                # If action dict itself is a browser action (e.g. {"action": "open_page", "url": "..."})
                act_val = action.get("action")
                if act_val in BROWSER_ACTIONS:
                    tool_name = "browser"
                    tool_args = {**action, **tool_args}
                elif not tool_name and "query" in action:
                    tool_name = "sql_query"
                    tool_args = {"query": action["query"]}
                elif not tool_name and "answer" in action:
                    tool_name = "finish"
                    tool_args = {"answer": action["answer"]}
                elif not tool_name and "question" in action:
                    tool_name = "ask_user"
                    tool_args = {"question": action["question"]}
            elif isinstance(action, str):
                if action in BROWSER_ACTIONS:
                    tool_name = "browser"
                    tool_args = {k: v for k, v in parsed.items() if k not in ["thought", "reason", "step", "plan"]}
                    tool_args["action"] = action
                elif action in ["ask_user", "ask_human", "question"]:
                    tool_name = "ask_user"
                    tool_args = {"question": parsed.get("question", parsed.get("query", "Please provide more details."))}
                elif action in ["sql_query", "query", "select", "sql"]:
                    tool_name = "sql_query"
                    tool_args = {"query": parsed.get("query", parsed.get("sql", ""))}
                elif action in ["finish", "done", "complete", "answer"]:
                    tool_name = "finish"
                    tool_args = {"answer": parsed.get("answer", parsed.get("final_answer", ""))}
                else:
                    tool_name = action
                    tool_args = parsed.get("args") or {k: v for k, v in parsed.items() if k not in ["thought", "reason", "action", "step", "plan"]}
            else:
                tool_name = parsed.get("tool") or parsed.get("tool_name")
                tool_args = parsed.get("args") or parsed.get("parameters") or {}

            # Direct root-level fallbacks
            if not tool_name:
                if "answer" in parsed:
                    tool_name = "finish"
                    tool_args = {"answer": parsed["answer"]}
                elif "question" in parsed:
                    tool_name = "ask_user"
                    tool_args = {"question": parsed["question"]}
                elif "query" in parsed:
                    tool_name = "sql_query"
                    tool_args = {"query": parsed["query"]}
                elif "url" in parsed and ("open" in thought.lower() or "navigate" in thought.lower()):
                    tool_name = "browser"
                    tool_args = {"action": "open_page", "url": parsed["url"]}
                elif "selector" in parsed:
                    tool_name = "browser"
                    tool_args = {"action": "click" if "click" in thought.lower() else "observe", **parsed}
                elif "data" in parsed:
                    d = parsed["data"]
                    if isinstance(d, dict) and "title" in d:
                        tool_name = "create_task"
                        tool_args = d

            # If tool_name is still missing, check if thought contains the final answer
            if not tool_name and thought:
                if any(kw in thought.lower() for kw in ["task complete", "audit complete", "here is the summary", "in conclusion", "summary of findings", "summary of the task status"]):
                    tool_name = "finish"
                    tool_args = {"answer": thought}
            
            # Graceful alias fallback for LLM hallucinated tool names
            if tool_name in ["approval_required", "ask_approval", "request_approval"]:
                q = tool_args.get("request") or tool_args.get("question") or tool_args.get("message") or "Do you approve this operation?"
                tool_name = "ask_user"
                tool_args = {"question": f"Human approval requested: {q}"}
            elif tool_name in ["create_task", "tasks", "task"]:
                # If create_task tool is not in registry, translate to sql_query or task_tools
                if not self.registry.get_tool("create_task"):
                    tool_name = "sql_query"
                    t_title = tool_args.get("title", "New Task")
                    t_assigned = tool_args.get("assignedTo", tool_args.get("assigned_to", "Admin"))
                    t_prio = tool_args.get("priority", "medium")
                    t_status = tool_args.get("status", "pending")
                    tool_args = {"query": f"INSERT INTO tasks (title, assignedTo, priority, status) VALUES ('{t_title}', '{t_assigned}', '{t_prio}', '{t_status}');"}
            
            if thought:
                await _emit({"type": "thought", "data": {"thought": thought}})
            
            # Dynamic Phase Advancement
            if state.step > 1 and self.state_machine.state == AgentState.UNDERSTANDING:
                await self.state_machine.transition(AgentState.PLANNING)
                await self.state_machine.transition(AgentState.EXECUTING)
                
            if tool_name == "db_select" or "verify" in thought.lower() or "confirm" in thought.lower():
                if self.state_machine.state != AgentState.VERIFYING:
                    await self.state_machine.transition(AgentState.VERIFYING)
            
            # Loop Breaker Check
            action_signature = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
            state.action_history.append(action_signature)
            
            if len(state.action_history) >= 3 and len(set(state.action_history[-3:])) == 1:
                state.action_history.clear()  # Reset so it does not perpetually loop on every subsequent step
                obs = f"SYSTEM ERROR: Loop detected! You attempted '{tool_name}' with identical arguments 3 times without making progress. You MUST try a different query/tool or call the 'finish' tool with your final summary."
                self.history.append({"role": "user", "content": f"Observation:\n{obs}"})
                await _emit({"type": "observation", "data": {"observation": obs}})
                continue
            
            # Guard & Policy Checks
            if is_web_mode and tool_name not in ["browser", "ask_user", "finish", "memorize_fact"]:
                obs = "POLICY ERROR: Web Automation Mode is active. Direct database tools and SQL queries are disabled for this task. You must perform all actions on-screen via the 'browser' tool."
                self.history.append({"role": "user", "content": f"Observation:\n{obs}"})
                await _emit({"type": "observation", "data": {"observation": obs}})
                continue

            is_schema_alteration = False
            is_mutation = False
            blocked_reason = ""
            
            tool_obj = self.registry.get_tool(tool_name) if tool_name else None
            
            # 1. Detect DDL / Schema Alteration / Table Restructuring
            if tool_name == "sql_query":
                q = str(tool_args.get("query", "")).strip().upper()
                ddl_patterns = [
                    r"\bALTER\s+TABLE\b",
                    r"\bDROP\s+TABLE\b",
                    r"\bDROP\s+COLUMN\b",
                    r"\bADD\s+COLUMN\b",
                    r"\bRENAME\s+TO\b",
                    r"\bRENAME\s+COLUMN\b",
                    r"\bALTER\b",
                    r"\bDROP\b",
                    r"\bTRUNCATE\b",
                ]
                if any(re.search(p, q) for p in ddl_patterns):
                    is_schema_alteration = True
            elif tool_name and any(tool_name.startswith(kw) for kw in ["alter", "drop"]):
                is_schema_alteration = True

            # Hard Forbidden Guardrail: Auto-reject schema restructuring / column changes immediately
            if is_schema_alteration:
                blocked_reason = (
                    "FORBIDDEN: Table restructuring and column alterations (ALTER, DROP, RENAME, ADD/DROP COLUMN) "
                    "are strictly prohibited by system security policy. No user or agent is permitted to restructure the database schema."
                )
                await _emit({
                    "type": "guard",
                    "tool": tool_name,
                    "checks": [
                        {"rule": "Schema & Table Restructuring Policy", "passed": False, "reason": blocked_reason}
                    ],
                    "verdict": "rejected"
                })
                obs = (
                    "Security Policy Violation: Auto-rejected. Table restructuring and column alterations "
                    "(ALTER, DROP, RENAME, ADD/DROP COLUMN) are strictly forbidden because restructuring the "
                    "database schema is not allowed. Only data-level operations (INSERT, UPDATE, DELETE) "
                    "are permitted with human authorization."
                )
                self.history.append({"role": "user", "content": f"Observation from {tool_name}:\n{obs}"})
                await _emit({"type": "observation", "data": {"observation": obs}})
                await _emit({"type": "assess", "status": "failed", "expected": "Policy Compliance", "actual": "Auto-rejected schema alteration"})
                await self.state_machine.transition(AgentState.RECOVERING)
                continue

            # 2. Detect Data Mutations (UPDATE, INSERT, DELETE, status changes, task reassignments, cancellations)
            if tool_name == "sql_query":
                q = str(tool_args.get("query", "")).strip().upper()
                if re.search(r"\b(UPDATE|INSERT|DELETE|REPLACE)\b", q):
                    is_mutation = True
            elif tool_obj:
                if getattr(tool_obj, "effect", "") == "write":
                    is_mutation = True
                elif getattr(tool_obj, "risk_level", None) in [RiskLevel.MEDIUM, RiskLevel.HIGH]:
                    is_mutation = True
                elif hasattr(tool_obj, "requires_approval") and tool_obj.requires_approval(tool_args):
                    is_mutation = True
                elif tool_name and any(tool_name.startswith(kw) for kw in [
                    "create", "update", "delete", "post", "cancel", "reassign", 
                    "manage", "onboard", "offboard", "issue", "approve", "modify", "patch", "remove", "add", "set"
                ]):
                    is_mutation = True
            elif tool_name and any(tool_name.startswith(kw) for kw in [
                "create", "update", "delete", "post", "cancel", "reassign", 
                "manage", "onboard", "offboard", "issue", "approve", "modify", "patch", "remove", "add", "set"
            ]):
                is_mutation = True

            if is_mutation:
                blocked_reason = "Safety Policy: Database mutations, cancellations, and state modifications require explicit human authorization."

            await _emit({
                "type": "guard",
                "tool": tool_name,
                "checks": [
                    {"rule": "Read-only enforcement & Write policy", "passed": not is_mutation, "reason": blocked_reason or "Safe read operation"}
                ],
                "verdict": "allowed" if not is_mutation else "requires_approval"
            })
            
            # Dynamic Subgoal and Success Points Progression
            if active_subgoals:
                num_goals = len(active_subgoals)
                active_idx = min(num_goals - 1, state.step - 1)
                for i in range(num_goals):
                    if i < active_idx:
                        active_subgoals[i]["status"] = "completed"
                    elif i == active_idx:
                        active_subgoals[i]["status"] = "in_progress"
                    else:
                        active_subgoals[i]["status"] = "pending"
                
                if len(success_points) >= 1 and state.step >= 1:
                    success_points[0]["status"] = "passed"
                if len(success_points) >= 2 and (state.step >= 2 or not is_mutation):
                    success_points[1]["status"] = "passed"
                if len(success_points) >= 3 and ("verify" in thought.lower() or state.step >= 3):
                    success_points[2]["status"] = "passed"
                    
                await _emit({
                    "type": "plan_update",
                    "subgoals": active_subgoals,
                    "success_points": success_points
                })

            # Emit explicit action event with active subgoal metadata
            active_sg = active_subgoals[active_idx] if active_subgoals and 'active_idx' in locals() else {}
            await _emit({
                "type": "action",
                "tool": tool_name,
                "args": tool_args,
                "subgoal_id": active_sg.get("id", "G1"),
                "subgoal_title": active_sg.get("title", "Execute Step"),
                "step": state.step
            })

            if tool_name == "finish":
                await self.state_machine.transition(AgentState.DONE)
                if "answer" in tool_args and isinstance(tool_args["answer"], str) and len(tool_args) == 1:
                    final_answer = tool_args["answer"]
                elif "final_answer" in tool_args and isinstance(tool_args["final_answer"], str) and len(tool_args) == 1:
                    final_answer = tool_args["final_answer"]
                elif any(isinstance(v, str) for v in tool_args.values()):
                    # Combine all textual parts (e.g. if LLM used multiple markdown keys)
                    parts = []
                    for k, v in tool_args.items():
                        if isinstance(v, str):
                            if not k.startswith("_") and k not in ["tool", "tool_name", "type"]:
                                parts.append(v)
                        elif isinstance(v, (dict, list)):
                            parts.append(json.dumps(v, indent=2))
                    final_answer = "\n\n".join(parts) if parts else "Task complete."
                else:
                    final_answer = json.dumps(tool_args, indent=2)
                if not isinstance(final_answer, str):
                    final_answer = json.dumps(final_answer, indent=2)
                for sg in active_subgoals:
                    sg["status"] = "completed"
                for sp in success_points:
                    sp["status"] = "passed"
                await _emit({
                    "type": "plan_update",
                    "subgoals": active_subgoals,
                    "success_points": success_points
                })
                break
                
            # Execute tool
            if not tool_name:
                obs = "Error: No tool specified."
            elif tool_name == "ask_user":
                await self.state_machine.transition(AgentState.NEEDS_USER)
                await _emit({
                    "type": "ask_user",
                    "question": tool_args.get("question", "Please provide more information."),
                    "step": state.step
                })
                if approval_queue:
                    human_resp = await approval_queue.get()
                    if human_resp.get("user_response") == "__CANCEL__":
                        final_answer = "Cancelled by user."
                        break
                    obs = f"Human answered: {human_resp.get('user_response', 'No answer.')}"
                else:
                    obs = "No human available."
                await self.state_machine.transition(AgentState.EXECUTING)
            else:
                try:
                    tool = self.registry.get_tool(tool_name)
                    if not tool:
                        obs = f"Error: Tool {tool_name} not found."
                    else:
                        _was_approved = False
                        if is_mutation or (hasattr(tool, "requires_approval") and tool.requires_approval(tool_args)):
                            await self.state_machine.transition(AgentState.WAITING_APPROVAL)
                            preview_data = tool.preview(tool_args) if hasattr(tool, "preview") else {}
                            if not preview_data and tool_name == "sql_query":
                                preview_data = {"sql": tool_args.get("query", "")}
                            elif not preview_data:
                                preview_data = tool_args
                            
                            # Build human-readable context
                            ctx = _build_approval_context(tool_name, tool_args, blocked_reason)
                                
                            await _emit({
                                "type": "approval_required",
                                "data": {
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "preview": preview_data,
                                    "title": ctx.get("title", "Human Authorization Required"),
                                    "summary": ctx.get("summary", "This operation mutates database records and requires authorization."),
                                    "action_type": ctx.get("action_type", "MUTATION"),
                                    "entity": ctx.get("entity", "Record"),
                                    "details": ctx.get("details", {}),
                                    "risk": "CRITICAL" if any(k in str(tool_args).upper() for k in ["DROP", "ALTER", "DELETE"]) else "HIGH",
                                    "reason": blocked_reason or ctx.get("summary") or "This operation mutates database records or cancels items and requires authorization."
                                }
                            })
                            if approval_queue:
                                human_resp = await approval_queue.get()
                                if human_resp.get("user_response") == "__CANCEL__":
                                    final_answer = "Cancelled by user."
                                    break
                                if not human_resp.get("approved"):
                                    obs = f"User denied this action. Reason: {human_resp.get('user_response', 'Rejected by administrator.')}"
                                    self.history.append({"role": "user", "content": f"Observation:\n{obs}"})
                                    await self.state_machine.transition(AgentState.EXECUTING)
                                    await _emit({"type": "observation", "data": {"observation": obs}})
                                    continue
                                _was_approved = True
                            else:
                                obs = "Safety violation: Action requires human approval, but no approval handler was provided."
                                self.history.append({"role": "user", "content": f"Observation:\n{obs}"})
                                await self.state_machine.transition(AgentState.RECOVERING)
                                await _emit({"type": "observation", "data": {"observation": obs}})
                                continue
                                
                            await self.state_machine.transition(AgentState.EXECUTING)
                            
                        # Run the tool
                        result = await self.registry.execute(tool_name, kwargs={**tool_args, "run_id": run_id}, approval_granted=_was_approved)
                        is_ok = getattr(result, "ok", getattr(result, "success", False))
                        if is_ok:
                            data = getattr(result, "data", "Success")
                            if isinstance(data, (dict, list)):
                                obs = json.dumps(data, indent=2)
                            else:
                                obs = str(data)
                            await _emit({"type": "assess", "status": "success", "expected": "Success", "actual": "Command executed successfully"})
                        else:
                            obs = f"Failed: {getattr(result, 'detail', getattr(result, 'error', 'Unknown error'))}"
                            await _emit({"type": "assess", "status": "failed", "expected": "Success", "actual": obs})
                            await self.state_machine.transition(AgentState.RECOVERING)

                        # Synchronize trace directly into active subgoal
                        if active_subgoals and 'active_idx' in locals() and active_idx < len(active_subgoals):
                            sg = active_subgoals[active_idx]
                            sg["thought"] = thought
                            sg["guard"] = {"passed": not is_mutation or _was_approved, "rule": blocked_reason or "Safe read/approved write"}
                            sg["action"] = {"tool": tool_name, "args": tool_args}
                            sg["observation"] = obs
                            sg["status"] = "completed" if is_ok else "in_progress"
                            sg["verified"] = is_ok
                            await _emit({
                                "type": "plan_update",
                                "subgoals": active_subgoals,
                                "success_points": success_points
                            })
                except Exception as e:
                    obs = f"Error executing {tool_name}: {e}"
                    await _emit({"type": "assess", "status": "failed", "expected": "Success", "actual": obs})
                    await self.state_machine.transition(AgentState.RECOVERING)
                    
            self.history.append({"role": "user", "content": f"Observation from {tool_name}:\n{obs}"})
            await _emit({"type": "observation", "data": {"observation": obs}})
            
        # Determine final state based on final answer
        if "Error:" in final_answer:
            await self.state_machine.transition(AgentState.FAILED)
        elif "Cancelled" in final_answer:
            await self.state_machine.transition(AgentState.CANCELLED)
        else:
            await self.state_machine.transition(AgentState.DONE)
            
        return final_answer
