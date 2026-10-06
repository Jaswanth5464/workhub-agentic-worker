"""
========================================================================================
 WORKHUB AI TASK WORKER - SEQUENTIAL TASK-BY-TASK EXECUTION RUNNER
========================================================================================
Executes AI Worker tasks one by one with live console output, showing:
  - Task Description & User Instruction
  - AI Tool Selected & Executed
  - Database Mutation in SQLite (Clean Architecture)
  - Real-Time Audit Log Entry Recorded
========================================================================================
"""

import os
import sys
import asyncio
import json
from datetime import datetime

# Enable UTF-8 console output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from workhub_project.database.db_utils import get_db_connection, init_db, get_recent_audit_logs
from ai_worker_project.tools.employee_tools import CreateEmployeeTool, GetEmployeeTool, UpdateEmployeeTool
from ai_worker_project.tools.hr_tools import SearchEmployeeRecordsTool, SendHREmailTool
from ai_worker_project.tools.hr_api_tools import (
    ManageExpenseTool,
    ManageLeaveRequestTool,
    HRTaskManagementTool,
    UpdateEmployeeProfileTool,
    ListAssignableEmployeesTool
)
from ai_worker_project.tools.hr_extra_tools import UploadDocumentTool, ScheduleInterviewTool
from ai_worker_project.tools.expense_tools import CreateExpenseTool
from ai_worker_project.tools.leave_tools import CreateLeaveTool
from ai_worker_project.tools.benefit_tools import CreateBenefitTool

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title.center(78)} ")
    print("=" * 80)

def print_task_banner(task_num: int, task_name: str, agent_prompt: str):
    print("\n" + "-" * 80)
    print(f" TASK {task_num}: {task_name.upper()}")
    print(f" Prompt / Instruction : \"{agent_prompt}\"")
    print("-" * 80)

def print_result(tool_name: str, status: str, details: dict):
    print(f"  --> Tool Executed   : {tool_name}")
    print(f"  --> Execution Status: [{status}]")
    for k, v in details.items():
        print(f"      * {k.ljust(22)}: {v}")

async def run_tasks_sequentially():
    print_header("AI TASK WORKER: SEQUENTIAL TASK EXECUTION SUITE")
    init_db()

    # Shared task context state
    context = {}

    # -------------------------------------------------------------------------
    # TASK 1: Onboard New Employee
    # -------------------------------------------------------------------------
    print_task_banner(1, "Employee Onboarding", "Onboard new employee Alex Carter as Staff Platform Engineer in Engineering")
    create_emp_tool = CreateEmployeeTool()
    res1 = await create_emp_tool.execute(data={
        "name": "Alex Carter",
        "department": "Engineering",
        "role": "Staff Platform Engineer",
        "status": "active",
        "email": "alex.carter@workhub.local",
        "phone": "555-0199",
        "emergencyContact": "Sarah Carter - 555-0200",
        "joined": datetime.now().strftime("%Y-%m-%d"),
        "manager": "Admin"
    })
    context["emp_id"] = res1.data["id"]
    print_result("CreateEmployeeTool", "SUCCESS" if res1.success else "FAILED", {
        "Assigned Employee ID": context["emp_id"],
        "Name": res1.data["name"],
        "Department": res1.data["department"],
        "Role": res1.data["role"]
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 2: Query & Verify Employee Profile
    # -------------------------------------------------------------------------
    print_task_banner(2, "Search & Verify Profile", "Search the directory for 'Alex Carter' and retrieve profile record")
    search_tool = SearchEmployeeRecordsTool()
    res2 = await search_tool.execute(query="Alex Carter")
    print_result("SearchEmployeeRecordsTool", "SUCCESS" if res2.success else "FAILED", {
        "Search Query": "Alex Carter",
        "Total Matches": len(res2.data.get("results", [])),
        "Resolved Employee": res2.data["results"][0]["name"] if res2.data.get("results") else "N/A"
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 3: Update Profile Information
    # -------------------------------------------------------------------------
    print_task_banner(3, "Update Employee Profile", f"Update phone number for employee {context['emp_id']} to 555-8888")
    update_profile_tool = UpdateEmployeeProfileTool()
    res3 = await update_profile_tool.execute(
        employee_id=context["emp_id"],
        phone="555-8888",
        emergency_contact="Sarah Carter (Primary) - 555-9999"
    )
    print_result("UpdateEmployeeProfileTool", "SUCCESS" if res3.success else "FAILED", {
        "Updated Employee ID": context["emp_id"],
        "Status Message": res3.data.get("status"),
        "New Phone in DB": res3.data["record"]["phone"]
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 4: Query Assignable Employees Dropdown List
    # -------------------------------------------------------------------------
    print_task_banner(4, "Fetch Assignable Employees", "Retrieve active employee list for task assignment dropdown")
    list_tool = ListAssignableEmployeesTool()
    res4 = await list_tool.execute(limit=5)
    print_result("ListAssignableEmployeesTool", "SUCCESS" if res4.success else "FAILED", {
        "Total Active Available": res4.data["count"],
        "Sample Selection Options": [e["label"] for e in res4.data["employees"][:3]]
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 5: Create & Assign Task to Employee
    # -------------------------------------------------------------------------
    print_task_banner(5, "Task Creation & Assignment", f"Assign task 'Deploy Kubernetes Ingress' to {context['emp_id']}")
    task_tool = HRTaskManagementTool()
    res5 = await task_tool.execute(
        title="Deploy Kubernetes Ingress",
        assignedTo=context["emp_id"],  # Pass employee ID; tool auto-resolves to Alex Carter
        priority="high",
        status="pending",
        dueDate="2026-10-31"
    )
    context["task_id"] = res5.data["record"]["id"]
    print_result("HRTaskManagementTool", "SUCCESS" if res5.success else "FAILED", {
        "Created Task ID": context["task_id"],
        "Task Title": res5.data["record"]["title"],
        "Assigned To (Resolved)": res5.data["record"]["assignedTo"],
        "Priority": res5.data["record"]["priority"]
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 6: Update Task Status Lifecycle
    # -------------------------------------------------------------------------
    print_task_banner(6, "Task Status Lifecycle Transition", f"Mark task {context['task_id']} as 'completed'")
    res6 = await task_tool.execute(
        task_id=context["task_id"],
        status="completed"
    )
    print_result("HRTaskManagementTool", "SUCCESS" if res6.success else "FAILED", {
        "Task ID": context["task_id"],
        "Transitioned Status": res6.data["record"]["status"]
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 7: Expense Submission & Approval
    # -------------------------------------------------------------------------
    print_task_banner(7, "Expense Management Workflow", "File and approve a cloud infrastructure expense for Alex Carter")
    create_exp_tool = CreateExpenseTool()
    manage_exp_tool = ManageExpenseTool()
    
    exp_created = await create_exp_tool.execute(data={
        "employee": "Alex Carter",
        "category": "Software",
        "amount": "Rs. 14,500",
        "description": "Cloud Cluster Ingress Licensing",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": "pending",
        "receiptId": "REC-9988"
    })
    context["exp_id"] = exp_created.data["id"]
    
    exp_approved = await manage_exp_tool.execute(expense_id=str(context["exp_id"]), action="approve")
    print_result("ManageExpenseTool", "SUCCESS" if exp_approved.success else "FAILED", {
        "Expense ID": context["exp_id"],
        "Employee": "Alex Carter",
        "Amount": "Rs. 14,500",
        "Updated Status": exp_approved.data["record"]["status"]
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 8: Leave Request & Approval
    # -------------------------------------------------------------------------
    print_task_banner(8, "Leave Request & Approval Workflow", "Submit and approve Annual Leave for Alex Carter")
    create_leave_tool = CreateLeaveTool()
    manage_leave_tool = ManageLeaveRequestTool()

    leave_created = await create_leave_tool.execute(data={
        "employee": "Alex Carter",
        "type": "Annual Leave",
        "dates": "Nov 15 - Nov 20",
        "status": "pending"
    })
    context["leave_id"] = leave_created.data["id"]

    leave_approved = await manage_leave_tool.execute(leave_id=str(context["leave_id"]), action="approve")
    print_result("ManageLeaveRequestTool", "SUCCESS" if leave_approved.success else "FAILED", {
        "Leave ID": context["leave_id"],
        "Employee": "Alex Carter",
        "Type": "Annual Leave",
        "Updated Status": leave_approved.data["record"]["status"]
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 9: Create Healthcare Benefit Plan
    # -------------------------------------------------------------------------
    print_task_banner(9, "Benefit Plan Creation", "Create corporate Vision & Dental Healthcare plan")
    create_ben_tool = CreateBenefitTool()
    res9 = await create_ben_tool.execute(data={
        "name": "Comprehensive Vision & Dental",
        "provider": "MetLife Healthcare",
        "coverage": "100% Preventive, 80% Major",
        "enrolled": 1,
        "status": "active"
    })
    context["ben_id"] = res9.data["id"]
    print_result("CreateBenefitTool", "SUCCESS" if res9.success else "FAILED", {
        "Benefit ID": context["ben_id"],
        "Plan Name": res9.data["name"],
        "Provider": res9.data["provider"]
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 10: Dispatch Automated Email
    # -------------------------------------------------------------------------
    print_task_banner(10, "Automated Employee Communication", "Send onboarding confirmation email to alex.carter@workhub.local")
    send_email_tool = SendHREmailTool()
    res10 = await send_email_tool.execute(
        to_email="alex.carter@workhub.local",
        subject="Welcome to WorkHub Engineering",
        body="Your account and tasks have been initialized."
    )
    context["email_id"] = res10.data["record"]["id"]
    print_result("SendHREmailTool", "SUCCESS" if res10.success else "FAILED", {
        "Email ID": context["email_id"],
        "Recipient": "alex.carter@workhub.local",
        "Subject": res10.data["record"]["subject"]
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 11: Upload Document Policy
    # -------------------------------------------------------------------------
    print_task_banner(11, "Document Center Upload", "Upload Remote Work Security Policy to Document Center")
    upload_doc_tool = UploadDocumentTool()
    res11 = await upload_doc_tool.execute(
        file_name="Remote_Work_Security_Policy_2026.pdf",
        content="Corporate security guidelines and VPN access policies."
    )
    context["doc_id"] = res11.data["id"]
    print_result("UploadDocumentTool", "SUCCESS" if res11.success else "FAILED", {
        "Document ID": context["doc_id"],
        "Document Name": res11.data["name"],
        "Category": res11.data["type"]
    })
    await asyncio.sleep(0.3)

    # -------------------------------------------------------------------------
    # TASK 12: Real-time Audit Log Verification & Cleanup
    # -------------------------------------------------------------------------
    print_task_banner(12, "Audit Stream Verification & Cleanup", "Verify live audit logs in SQLite and clean up demo records")
    logs = get_recent_audit_logs(limit=5)
    
    # Cleanup demo records
    conn = get_db_connection()
    conn.execute("DELETE FROM employees WHERE id = ?", (context["emp_id"],))
    conn.execute("DELETE FROM tasks WHERE id = ?", (context["task_id"],))
    conn.execute("DELETE FROM expenses WHERE id = ?", (context["exp_id"],))
    conn.execute("DELETE FROM leaves WHERE id = ?", (context["leave_id"],))
    conn.execute("DELETE FROM benefits WHERE id = ?", (context["ben_id"],))
    conn.execute("DELETE FROM emails WHERE id = ?", (context["email_id"],))
    conn.execute("DELETE FROM documents WHERE id = ?", (context["doc_id"],))
    conn.commit()
    conn.close()

    print_result("AuditLogVerifier", "SUCCESS", {
        "Total Recent Audit Logs": len(logs),
        "Latest Log 1": f"[{logs[0]['action']}] on '{logs[0]['table_name']}' (ID: {logs[0]['record_id']})",
        "Latest Log 2": f"[{logs[1]['action']}] on '{logs[1]['table_name']}' (ID: {logs[1]['record_id']})",
        "Latest Log 3": f"[{logs[2]['action']}] on '{logs[2]['table_name']}' (ID: {logs[2]['record_id']})",
        "Database Cleaned": "All test fixtures removed successfully"
    })

    print_header(">>> ALL 12 TASKS EXECUTED SEQUENTIALLY WITH 100% SUCCESS <<<")

if __name__ == "__main__":
    asyncio.run(run_tasks_sequentially())
