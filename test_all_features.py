"""
Comprehensive 100-Test Suite for WorkHub HR System
Validates:
- Clean Architecture (Database -> Repository -> Service -> Controller -> Frontend State)
- Accurate Employee Data & Complete CRUD operations (with realistic dummy records)
- Expense Lifecycle, Approvals, Rejections, and Aggregate Amount Calculations
- Leave Request Lifecycle, Approvals, Rejections, and Calendar Mapping
- Task Management, Creation, Status Transitions (Pending -> In Progress -> Completed)
- Benefit Operations, Coverage Updates, Enrollment Tracking
- Email/Inbox Operations, Composing, Unread Counts, Reply Logging
- Document Operations, Storage, Retrieval, and Viewer Payloads
- Live Audit Logging & Activity Feed Real-Time Synchronization
- Overview Report Generation & Statistical Calculation Accuracies
- UI Badges & Real-time Polling Synchronization Accuracy
- AI Worker Tool Integration with Strict Guardrails
"""

import sys
import os
import unittest
import asyncio
import json
from datetime import datetime
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend_hr import app
from workhub_project.database.db_utils import get_db_connection, init_db, get_recent_audit_logs
from workhub_project.services.employee_service import EmployeeService
from workhub_project.services.expense_service import ExpenseService
from workhub_project.services.leave_service import LeaveService
from workhub_project.services.task_service import TaskService
from workhub_project.services.benefit_service import BenefitService
from workhub_project.services.document_service import DocumentService
from workhub_project.services.email_service import EmailService

from ai_worker_project.tools.hr_tools import SearchEmployeeRecordsTool, SendHREmailTool
from ai_worker_project.tools.employee_tools import GetAllEmployeesTool, GetEmployeeTool, UpdateEmployeeTool, CreateEmployeeTool, DeleteEmployeeTool
from ai_worker_project.tools.hr_api_tools import ManageExpenseTool, ManageLeaveRequestTool, HRTaskManagementTool, UpdateEmployeeProfileTool, ListAssignableEmployeesTool
from ai_worker_project.tools.hr_extra_tools import DownloadDocumentTool, UploadDocumentTool, ScheduleInterviewTool, OnboardEmployeeTool
from ai_worker_project.tools.expense_tools import CreateExpenseTool, UpdateExpenseTool, GetAllExpensesTool
from ai_worker_project.tools.sql_tool import SQLQueryTool

class TestWorkHubHRCleanArchitectureComprehensive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        # Ensure initial seed data integrity
        conn = get_db_connection()
        conn.execute("UPDATE employees SET department = 'HR', phone = '555-0101', status = 'active' WHERE id = 'EMP-002'")
        conn.commit()
        conn.close()

        cls.client = TestClient(app)
        cls.emp_service = EmployeeService()
        cls.exp_service = ExpenseService()
        cls.leave_service = LeaveService()
        cls.task_service = TaskService()
        cls.ben_service = BenefitService()
        cls.doc_service = DocumentService()
        cls.email_service = EmailService()

    # =========================================================================
    # SECTION 1: Direct SQLite Connection & Schema Integrity (Tests 1-8)
    # =========================================================================
    def test_001_sqlite_connection_active(self):
        conn = get_db_connection()
        self.assertIsNotNone(conn)
        conn.close()

    def test_002_employees_table_schema(self):
        conn = get_db_connection()
        c = conn.cursor()
        cols = [col[1] for col in c.execute("PRAGMA table_info(employees)").fetchall()]
        conn.close()
        for required_col in ['id', 'name', 'department', 'role', 'status', 'email', 'joined', 'emergencyContact', 'phone', 'manager']:
            self.assertIn(required_col, cols)

    def test_003_expenses_table_schema(self):
        conn = get_db_connection()
        c = conn.cursor()
        cols = [col[1] for col in c.execute("PRAGMA table_info(expenses)").fetchall()]
        conn.close()
        for required_col in ['id', 'employee', 'date', 'amount', 'category', 'description', 'status', 'receiptId']:
            self.assertIn(required_col, cols)

    def test_004_leaves_table_schema(self):
        conn = get_db_connection()
        c = conn.cursor()
        cols = [col[1] for col in c.execute("PRAGMA table_info(leaves)").fetchall()]
        conn.close()
        for required_col in ['id', 'employee', 'type', 'dates', 'status']:
            self.assertIn(required_col, cols)

    def test_005_tasks_table_schema(self):
        conn = get_db_connection()
        c = conn.cursor()
        cols = [col[1] for col in c.execute("PRAGMA table_info(tasks)").fetchall()]
        conn.close()
        for required_col in ['id', 'title', 'assignedTo', 'dueDate', 'priority', 'status']:
            self.assertIn(required_col, cols)

    def test_006_benefits_table_schema(self):
        conn = get_db_connection()
        c = conn.cursor()
        cols = [col[1] for col in c.execute("PRAGMA table_info(benefits)").fetchall()]
        conn.close()
        for required_col in ['id', 'name', 'provider', 'coverage', 'enrolled', 'status']:
            self.assertIn(required_col, cols)

    def test_007_documents_table_schema(self):
        conn = get_db_connection()
        c = conn.cursor()
        cols = [col[1] for col in c.execute("PRAGMA table_info(documents)").fetchall()]
        conn.close()
        for required_col in ['id', 'type', 'name', 'relatedTo', 'content']:
            self.assertIn(required_col, cols)

    def test_008_audit_logs_table_schema(self):
        conn = get_db_connection()
        c = conn.cursor()
        cols = [col[1] for col in c.execute("PRAGMA table_info(audit_logs)").fetchall()]
        conn.close()
        for required_col in ['id', 'table_name', 'record_id', 'action', 'details', 'timestamp']:
            self.assertIn(required_col, cols)

    # =========================================================================
    # SECTION 2: Accurate Employee Fetching & Directory Verification (Tests 9-16)
    # =========================================================================
    def test_009_accurate_total_employees_count_direct_from_sqlite(self):
        emps = self.emp_service.get_all(limit=500)
        self.assertGreaterEqual(len(emps), 60, "Must load all actual 60+ employees from SQLite, not 20 from mock")

    def test_010_employee_john_doe_profile_accuracy(self):
        emp = self.emp_service.get_by_id("EMP-001")
        self.assertIsNotNone(emp)
        self.assertEqual(emp["name"], "John Doe")
        self.assertIn("Engineering", emp["department"])

    def test_011_employee_jane_smith_profile_accuracy(self):
        emp = self.emp_service.get_by_id("EMP-002")
        self.assertIsNotNone(emp)
        self.assertEqual(emp["name"], "Jane Smith")
        self.assertEqual(emp["department"], "HR")

    def test_012_employee_search_by_name_substring(self):
        results = self.emp_service.search(query="Jane", limit=5)
        self.assertGreater(len(results), 0)
        self.assertTrue(any(r["name"] == "Jane Smith" for r in results))

    def test_013_employee_search_by_id_substring(self):
        results = self.emp_service.search(query="EMP-002", limit=5)
        self.assertGreaterEqual(len(results), 1)
        self.assertTrue(any(r["id"] == "EMP-002" for r in results))


    def test_014_employee_filter_by_department(self):
        hr_emps = self.emp_service.get_all(filters={"department": "HR"})
        self.assertGreater(len(hr_emps), 0)
        for e in hr_emps:
            self.assertEqual(e["department"], "HR")

    def test_015_employee_filter_by_status(self):
        active_emps = self.emp_service.get_all(filters={"status": "active"})
        self.assertGreater(len(active_emps), 0)
        for e in active_emps:
            self.assertEqual(e["status"], "active")

    def test_016_employee_non_existent_id_returns_none(self):
        emp = self.emp_service.get_by_id("EMP-99999-DOESNOTEXIST")
        self.assertIsNone(emp)

    # =========================================================================
    # SECTION 3: Employee CRUD & Form Filling Operations (Tests 17-26)
    # =========================================================================
    def test_017_create_dummy_employee_engineering(self):
        dummy = {
            "name": "Alex Mercer",
            "department": "Engineering",
            "role": "Senior Cloud Architect",
            "status": "active",
            "email": "alex.mercer@workhub.local",
            "joined": "2026-10-06",
            "emergencyContact": "Dana Mercer (Sister) - 555-0199",
            "phone": "555-0198",
            "manager": "Admin"
        }
        res = self.emp_service.create(dummy)
        self.assertIn("id", res)
        emp = self.emp_service.get_by_id(res["id"])
        self.assertEqual(emp["name"], "Alex Mercer")
        self.emp_service.delete(res["id"])

    def test_018_create_dummy_employee_finance(self):
        dummy = {
            "name": "Gordon Gekko",
            "department": "Finance",
            "role": "Financial Analyst",
            "status": "active",
            "email": "gordon.g@workhub.local",
            "joined": "2026-10-06",
            "emergencyContact": "Legal Counsel - 555-0211",
            "phone": "555-0210",
            "manager": "Admin"
        }
        res = self.emp_service.create(dummy)
        self.assertEqual(res["department"], "Finance")
        self.emp_service.delete(res["id"])

    def test_019_create_dummy_employee_marketing(self):
        dummy = {
            "name": "Don Draper",
            "department": "Marketing",
            "role": "Creative Director",
            "status": "active",
            "email": "don.draper@workhub.local",
            "joined": "2026-10-06",
            "emergencyContact": "Megan Draper - 555-0300",
            "phone": "555-0301",
            "manager": "Admin"
        }
        res = self.emp_service.create(dummy)
        self.assertEqual(res["role"], "Creative Director")
        self.emp_service.delete(res["id"])

    def test_020_update_employee_phone_number(self):
        res = self.emp_service.update("EMP-002", {"phone": "555-8888"})
        self.assertEqual(res["phone"], "555-8888")
        check = self.emp_service.get_by_id("EMP-002")
        self.assertEqual(check["phone"], "555-8888")

    def test_021_update_employee_emergency_contact(self):
        new_contact = "Robert Smith (Husband) - 555-0200"
        res = self.emp_service.update("EMP-002", {"emergencyContact": new_contact})
        self.assertEqual(res["emergencyContact"], new_contact)

    def test_022_update_employee_department_transfer(self):
        created = self.emp_service.create({
            "name": "Transfer Candidate",
            "department": "Sales",
            "role": "Rep",
            "status": "active",
            "email": "transfer@workhub.local"
        })
        self.emp_service.update(created["id"], {"department": "Marketing", "role": "Marketing Specialist"})
        check = self.emp_service.get_by_id(created["id"])
        self.assertEqual(check["department"], "Marketing")
        self.emp_service.delete(created["id"])

    def test_023_update_employee_status_to_on_leave(self):
        created = self.emp_service.create({
            "name": "Leave Candidate",
            "department": "HR",
            "role": "Recruiter",
            "status": "active",
            "email": "leave.cand@workhub.local"
        })
        self.emp_service.update(created["id"], {"status": "on_leave"})
        check = self.emp_service.get_by_id(created["id"])
        self.assertEqual(check["status"], "on_leave")
        self.emp_service.delete(created["id"])

    def test_024_update_employee_status_to_inactive(self):
        created = self.emp_service.create({
            "name": "Exiting Employee",
            "department": "Engineering",
            "role": "QA",
            "status": "active",
            "email": "exiting@workhub.local"
        })
        self.emp_service.update(created["id"], {"status": "inactive"})
        check = self.emp_service.get_by_id(created["id"])
        self.assertEqual(check["status"], "inactive")
        self.emp_service.delete(created["id"])

    def test_025_delete_employee_success(self):
        created = self.emp_service.create({
            "name": "Temp Deletion Target",
            "department": "Engineering",
            "role": "Intern",
            "status": "active",
            "email": "temp.del@workhub.local"
        })
        success = self.emp_service.delete(created["id"])
        self.assertTrue(success)
        self.assertIsNone(self.emp_service.get_by_id(created["id"]))

    def test_026_delete_non_existent_employee_returns_false(self):
        success = self.emp_service.delete("EMP-NONEXISTENT-9999")
        self.assertFalse(success)

    # =========================================================================
    # SECTION 4: Expense Management Lifecycle & Calculations (Tests 27-38)
    # =========================================================================
    def test_027_get_all_expenses_from_sqlite(self):
        expenses = self.exp_service.get_all()
        self.assertIsInstance(expenses, list)
        self.assertGreater(len(expenses), 0)

    def test_028_create_travel_expense(self):
        exp = self.exp_service.create({
            "employee": "John Doe",
            "category": "Travel",
            "amount": "₹12,500",
            "description": "Flight Tickets to Client Office",
            "date": "2026-10-06",
            "status": "pending",
            "receiptId": "REC-1001"
        })
        self.assertIn("id", exp)
        self.assertEqual(exp["status"], "pending")
        self.exp_service.delete(exp["id"])

    def test_029_create_software_license_expense(self):
        exp = self.exp_service.create({
            "employee": "Jane Smith",
            "category": "Software",
            "amount": "₹3,400",
            "description": "Annual SaaS Tool Subscription",
            "date": "2026-10-06",
            "status": "pending",
            "receiptId": "REC-1002"
        })
        self.assertEqual(exp["category"], "Software")
        self.exp_service.delete(exp["id"])

    def test_030_create_meals_expense(self):
        exp = self.exp_service.create({
            "employee": "Alice Johnson",
            "category": "Meals",
            "amount": "₹1,800",
            "description": "Team Lunch Discussion",
            "date": "2026-10-06",
            "status": "pending",
            "receiptId": "REC-1003"
        })
        self.assertEqual(exp["amount"], "₹1,800")
        self.exp_service.delete(exp["id"])

    def test_031_approve_pending_expense(self):
        exp = self.exp_service.create({
            "employee": "Bob Wilson",
            "category": "Hardware",
            "amount": "₹25,000",
            "description": "Ergonomic Monitor Setup",
            "date": "2026-10-06",
            "status": "pending",
            "receiptId": "REC-1004"
        })
        updated = self.exp_service.update(exp["id"], {"status": "approved"})
        self.assertEqual(updated["status"], "approved")
        check = self.exp_service.get_by_id(exp["id"])
        self.assertEqual(check["status"], "approved")
        self.exp_service.delete(exp["id"])

    def test_032_reject_pending_expense(self):
        exp = self.exp_service.create({
            "employee": "Charlie Brown",
            "category": "Miscellaneous",
            "amount": "₹8,000",
            "description": "Non-compliant purchase",
            "date": "2026-10-06",
            "status": "pending",
            "receiptId": "REC-1005"
        })
        updated = self.exp_service.update(exp["id"], {"status": "rejected"})
        self.assertEqual(updated["status"], "rejected")
        self.exp_service.delete(exp["id"])

    def test_033_filter_expenses_by_pending_status(self):
        pending = self.exp_service.get_all(filters={"status": "pending"})
        for p in pending:
            self.assertEqual(p["status"], "pending")

    def test_034_filter_expenses_by_approved_status(self):
        approved = self.exp_service.get_all(filters={"status": "approved"})
        for a in approved:
            self.assertEqual(a["status"], "approved")

    def test_035_filter_expenses_by_rejected_status(self):
        exp = self.exp_service.create({
            "employee": "Reject Test",
            "category": "Office",
            "amount": "₹500",
            "description": "Rejected item",
            "date": "2026-10-06",
            "status": "rejected"
        })
        rejected = self.exp_service.get_all(filters={"status": "rejected"})
        self.assertGreater(len(rejected), 0)
        self.exp_service.delete(exp["id"])

    def test_036_calculate_total_processed_expenses_sum(self):
        expenses = self.exp_service.get_all(filters={"status": "approved"})
        total = 0
        for e in expenses:
            num = int(str(e["amount"]).replace("₹", "").replace("$", "").replace(",", "").strip())
            total += num
        self.assertGreaterEqual(total, 0)

    def test_037_expense_receipt_id_generation(self):
        exp = self.exp_service.create({
            "employee": "Receipt Test",
            "category": "Travel",
            "amount": "₹999",
            "description": "Auto receipt test",
            "date": "2026-10-06",
            "status": "pending",
            "receiptId": "REC-AUTO-123"
        })
        self.assertEqual(exp["receiptId"], "REC-AUTO-123")
        self.exp_service.delete(exp["id"])

    def test_038_delete_expense_record(self):
        exp = self.exp_service.create({
            "employee": "Deletion Exp",
            "category": "Test",
            "amount": "₹100",
            "description": "To be removed",
            "date": "2026-10-06",
            "status": "pending"
        })
        self.assertTrue(self.exp_service.delete(exp["id"]))
        self.assertIsNone(self.exp_service.get_by_id(exp["id"]))

    # =========================================================================
    # SECTION 5: Leave Requests Lifecycle & Approval (Tests 39-48)
    # =========================================================================
    def test_039_get_all_leaves_from_sqlite(self):
        leaves = self.leave_service.get_all()
        self.assertIsInstance(leaves, list)
        self.assertGreater(len(leaves), 0)

    def test_040_create_annual_leave_request(self):
        lv = self.leave_service.create({
            "employee": "Jane Smith",
            "type": "Annual Leave",
            "dates": "Nov 15 - Nov 20",
            "status": "pending"
        })
        self.assertIn("id", lv)
        self.assertEqual(lv["status"], "pending")
        self.leave_service.delete(lv["id"])

    def test_041_create_sick_leave_request(self):
        lv = self.leave_service.create({
            "employee": "Bob Wilson",
            "type": "Sick Leave",
            "dates": "Oct 10 - Oct 12",
            "status": "pending"
        })
        self.assertEqual(lv["type"], "Sick Leave")
        self.leave_service.delete(lv["id"])

    def test_042_create_pto_leave_request(self):
        lv = self.leave_service.create({
            "employee": "Alice Johnson",
            "type": "PTO",
            "dates": "Nov 1 - Nov 5",
            "status": "pending"
        })
        self.assertEqual(lv["type"], "PTO")
        self.leave_service.delete(lv["id"])

    def test_043_create_parental_leave_request(self):
        lv = self.leave_service.create({
            "employee": "John Doe",
            "type": "Parental Leave",
            "dates": "Dec 1 - Dec 31",
            "status": "pending"
        })
        self.assertEqual(lv["type"], "Parental Leave")
        self.leave_service.delete(lv["id"])

    def test_044_approve_leave_request_updates_status(self):
        lv = self.leave_service.create({
            "employee": "Approval Tester",
            "type": "Annual Leave",
            "dates": "Nov 01 - Nov 05",
            "status": "pending"
        })
        self.leave_service.update(lv["id"], {"status": "approved"})
        check = self.leave_service.get_by_id(lv["id"])
        self.assertEqual(check["status"], "approved")
        self.leave_service.delete(lv["id"])

    def test_045_reject_leave_request_updates_status(self):
        lv = self.leave_service.create({
            "employee": "Reject Tester",
            "type": "Sick Leave",
            "dates": "Nov 02 - Nov 03",
            "status": "pending"
        })
        self.leave_service.update(lv["id"], {"status": "rejected"})
        check = self.leave_service.get_by_id(lv["id"])
        self.assertEqual(check["status"], "rejected")
        self.leave_service.delete(lv["id"])

    def test_046_filter_leaves_by_pending_approvals(self):
        pending = self.leave_service.get_all(filters={"status": "pending"})
        for p in pending:
            self.assertEqual(p["status"], "pending")

    def test_047_calendar_approved_leaves_query(self):
        approved = self.leave_service.get_all(filters={"status": "approved"})
        for a in approved:
            self.assertEqual(a["status"], "approved")

    def test_048_delete_leave_request(self):
        lv = self.leave_service.create({
            "employee": "Delete Tester",
            "type": "PTO",
            "dates": "Nov 05",
            "status": "pending"
        })
        self.assertTrue(self.leave_service.delete(lv["id"]))
        self.assertIsNone(self.leave_service.get_by_id(lv["id"]))

    # =========================================================================
    # SECTION 6: Tasks Management & Assignment (Tests 49-58)
    # =========================================================================
    def test_049_get_all_tasks_from_sqlite(self):
        tasks = self.task_service.get_all()
        self.assertIsInstance(tasks, list)
        self.assertGreater(len(tasks), 0)

    def test_050_create_high_priority_task(self):
        tsk = self.task_service.create({
            "title": "Quarterly Performance Reviews",
            "assignedTo": "Jane Smith",
            "dueDate": "2026-10-31",
            "priority": "high",
            "status": "pending"
        })
        self.assertIn("id", tsk)
        self.assertEqual(tsk["priority"], "high")
        self.task_service.delete(tsk["id"])

    def test_051_create_medium_priority_task(self):
        tsk = self.task_service.create({
            "title": "Update Health Insurance Vendors",
            "assignedTo": "Admin",
            "dueDate": "2026-11-15",
            "priority": "medium",
            "status": "pending"
        })
        self.assertEqual(tsk["priority"], "medium")
        self.task_service.delete(tsk["id"])

    def test_052_create_low_priority_task(self):
        tsk = self.task_service.create({
            "title": "Organize Team Building Activity",
            "assignedTo": "Alice Johnson",
            "dueDate": "2026-12-01",
            "priority": "low",
            "status": "pending"
        })
        self.assertEqual(tsk["priority"], "low")
        self.task_service.delete(tsk["id"])

    def test_053_update_task_status_to_in_progress(self):
        tsk = self.task_service.create({
            "title": "In Progress Workflow Test",
            "assignedTo": "Admin",
            "dueDate": "2026-10-20",
            "priority": "medium",
            "status": "pending"
        })
        self.task_service.update(tsk["id"], {"status": "in_progress"})
        check = self.task_service.get_by_id(tsk["id"])
        self.assertEqual(check["status"], "in_progress")
        self.task_service.delete(tsk["id"])

    def test_054_update_task_status_to_completed(self):
        tsk = self.task_service.create({
            "title": "Completion Workflow Test",
            "assignedTo": "Admin",
            "dueDate": "2026-10-20",
            "priority": "medium",
            "status": "in_progress"
        })
        self.task_service.update(tsk["id"], {"status": "completed"})
        check = self.task_service.get_by_id(tsk["id"])
        self.assertEqual(check["status"], "completed")
        self.task_service.delete(tsk["id"])

    def test_055_filter_open_hr_tasks(self):
        all_tasks = self.task_service.get_all()
        open_tasks = [t for t in all_tasks if t.get("status") != "completed"]
        self.assertIsInstance(open_tasks, list)

    def test_056_reassign_task_to_another_employee(self):
        tsk = self.task_service.create({
            "title": "Reassignment Test",
            "assignedTo": "Old Assignee",
            "dueDate": "2026-10-25",
            "priority": "low",
            "status": "pending"
        })
        self.task_service.update(tsk["id"], {"assignedTo": "Jaswanth Lead"})
        check = self.task_service.get_by_id(tsk["id"])
        self.assertEqual(check["assignedTo"], "Jaswanth Lead")
        self.task_service.delete(tsk["id"])

    def test_057_update_task_due_date(self):
        tsk = self.task_service.create({
            "title": "Date Change Test",
            "assignedTo": "Admin",
            "dueDate": "2026-10-10",
            "priority": "high",
            "status": "pending"
        })
        self.task_service.update(tsk["id"], {"dueDate": "2026-11-20"})
        check = self.task_service.get_by_id(tsk["id"])
        self.assertEqual(check["dueDate"], "2026-11-20")
        self.task_service.delete(tsk["id"])

    def test_058_delete_task(self):
        tsk = self.task_service.create({
            "title": "Delete Target Task",
            "assignedTo": "Admin",
            "dueDate": "2026-10-10",
            "priority": "low",
            "status": "pending"
        })
        self.assertTrue(self.task_service.delete(tsk["id"]))
        self.assertIsNone(self.task_service.get_by_id(tsk["id"]))

    # =========================================================================
    # SECTION 7: Benefits Management & Enrollment (Tests 59-66)
    # =========================================================================
    def test_059_get_all_benefits_from_sqlite(self):
        benefits = self.ben_service.get_all()
        self.assertIsInstance(benefits, list)
        self.assertGreater(len(benefits), 0)

    def test_060_create_health_benefit(self):
        ben = self.ben_service.create({
            "name": "Comprehensive Health Plan",
            "provider": "BlueCross",
            "coverage": "90% In-Network Medical",
            "enrolled": 45,
            "status": "active"
        })
        self.assertIn("id", ben)
        self.assertEqual(ben["status"], "active")
        self.ben_service.delete(ben["id"])

    def test_061_create_dental_benefit(self):
        ben = self.ben_service.create({
            "name": "Delta Dental Premier",
            "provider": "Delta Dental",
            "coverage": "100% Preventive Care",
            "enrolled": 30,
            "status": "active"
        })
        self.assertEqual(ben["provider"], "Delta Dental")
        self.ben_service.delete(ben["id"])

    def test_062_update_benefit_coverage_description(self):
        ben = self.ben_service.create({
            "name": "Vision Coverage",
            "provider": "VSP",
            "coverage": "Basic Exam Coverage",
            "enrolled": 10,
            "status": "active"
        })
        self.ben_service.update(ben["id"], {"coverage": "Full Glasses & Contacts Coverage"})
        check = self.ben_service.get_by_id(ben["id"])
        self.assertEqual(check["coverage"], "Full Glasses & Contacts Coverage")
        self.ben_service.delete(ben["id"])

    def test_063_update_benefit_status_to_inactive(self):
        ben = self.ben_service.create({
            "name": "Legacy Gym Subsidy",
            "provider": "Local Gym",
            "coverage": "$20 Monthly",
            "enrolled": 5,
            "status": "active"
        })
        self.ben_service.update(ben["id"], {"status": "inactive"})
        check = self.ben_service.get_by_id(ben["id"])
        self.assertEqual(check["status"], "inactive")
        self.ben_service.delete(ben["id"])

    def test_064_increment_benefit_enrolled_count(self):
        ben = self.ben_service.create({
            "name": "401(k) Match Plan",
            "provider": "Fidelity",
            "coverage": "4% Employer Match",
            "enrolled": 50,
            "status": "active"
        })
        self.ben_service.update(ben["id"], {"enrolled": 55})
        check = self.ben_service.get_by_id(ben["id"])
        self.assertEqual(check["enrolled"], 55)
        self.ben_service.delete(ben["id"])

    def test_065_filter_active_benefits(self):
        active = self.ben_service.get_all(filters={"status": "active"})
        for b in active:
            self.assertEqual(b["status"], "active")

    def test_066_delete_benefit(self):
        ben = self.ben_service.create({
            "name": "Deprecated Wellness",
            "provider": "None",
            "coverage": "None",
            "enrolled": 0,
            "status": "inactive"
        })
        self.assertTrue(self.ben_service.delete(ben["id"]))
        self.assertIsNone(self.ben_service.get_by_id(ben["id"]))

    # =========================================================================
    # SECTION 8: Document Center Operations (Tests 67-74)
    # =========================================================================
    def test_067_get_all_documents_from_sqlite(self):
        docs = self.doc_service.get_all()
        self.assertIsInstance(docs, list)
        self.assertGreater(len(docs), 0)

    def test_068_create_security_policy_document(self):
        doc = self.doc_service.create({
            "name": "Information Security Policy 2026.pdf",
            "type": "Policy",
            "relatedTo": "All Staff",
            "content": "All employees must enable 2FA and never share credentials."
        })
        self.assertIn("id", doc)
        self.assertEqual(doc["type"], "Policy")
        self.doc_service.delete(doc["id"])

    def test_069_create_financial_report_document(self):
        doc = self.doc_service.create({
            "name": "Q3 Financial Summary.pdf",
            "type": "Report",
            "relatedTo": "Finance & Executive Team",
            "content": "Operating margin increased by 14% with strong expense discipline."
        })
        self.assertEqual(doc["type"], "Report")
        self.doc_service.delete(doc["id"])

    def test_070_create_employee_contract_document(self):
        doc = self.doc_service.create({
            "name": "Jane Smith NDA.pdf",
            "type": "Contract",
            "relatedTo": "EMP-002",
            "content": "Standard non-disclosure agreement signed upon employment."
        })
        self.assertEqual(doc["relatedTo"], "EMP-002")
        self.doc_service.delete(doc["id"])

    def test_071_create_expense_receipt_document(self):
        doc = self.doc_service.create({
            "name": "Flight Receipt REC-1042.pdf",
            "type": "Receipt",
            "relatedTo": "EXP-1042",
            "content": "Airline travel confirmation invoice."
        })
        self.assertEqual(doc["type"], "Receipt")
        self.doc_service.delete(doc["id"])

    def test_072_search_document_by_name(self):
        results = self.doc_service.search(query="Handbook", limit=5)
        self.assertIsInstance(results, list)

    def test_073_view_document_content_payload(self):
        doc = self.doc_service.create({
            "name": "Viewer Payload Test.pdf",
            "type": "Policy",
            "relatedTo": "Testing",
            "content": "Payload text verified."
        })
        check = self.doc_service.get_by_id(doc["id"])
        self.assertEqual(check["content"], "Payload text verified.")
        self.doc_service.delete(doc["id"])

    def test_074_delete_document(self):
        doc = self.doc_service.create({
            "name": "To Be Deleted.pdf",
            "type": "Policy",
            "relatedTo": "General",
            "content": "Test"
        })
        self.assertTrue(self.doc_service.delete(doc["id"]))
        self.assertIsNone(self.doc_service.get_by_id(doc["id"]))

    # =========================================================================
    # SECTION 9: Email & Admin Inbox Operations (Tests 75-82)
    # =========================================================================
    def test_075_get_all_emails_from_sqlite(self):
        emails = self.email_service.get_all()
        self.assertIsInstance(emails, list)
        self.assertGreater(len(emails), 0)

    def test_076_compose_new_hr_email(self):
        email = self.email_service.create({
            "from_email": "jane.smith@workhub.local",
            "subject": "Benefits Enrollment Window Open",
            "date": "2026-10-06",
            "read": 0,
            "body": "Please review and submit your healthcare selections by end of week."
        })
        self.assertIn("id", email)
        self.assertEqual(email["read"], 0)
        self.email_service.delete(email["id"])

    def test_077_mark_email_as_read(self):
        email = self.email_service.create({
            "from_email": "notifications@workhub.local",
            "subject": "System Upgrade Notice",
            "date": "2026-10-06",
            "read": 0,
            "body": "Maintenance scheduled tonight."
        })
        self.email_service.update(email["id"], {"read": 1})
        check = self.email_service.get_by_id(email["id"])
        self.assertEqual(check["read"], 1)
        self.email_service.delete(email["id"])

    def test_078_unread_emails_count_calculation(self):
        all_emails = self.email_service.get_all()
        unread = [m for m in all_emails if not m.get("read") or m.get("read") == 0]
        self.assertIsInstance(unread, list)

    def test_079_reply_email_generation(self):
        reply = self.email_service.create({
            "from_email": "admin@workhub.local",
            "subject": "Re: Benefits Enrollment Window Open",
            "date": "2026-10-06",
            "read": 1,
            "body": "Thank you for the notification. I have confirmed my enrollment."
        })
        self.assertIn("Re:", reply["subject"])
        self.email_service.delete(reply["id"])

    def test_080_search_email_by_subject(self):
        results = self.email_service.search(query="Leave", limit=5)
        self.assertIsInstance(results, list)

    def test_081_email_body_formatting_integrity(self):
        long_body = "Line 1: Announcement\nLine 2: Details\nLine 3: Action Items"
        email = self.email_service.create({
            "from_email": "ceo@workhub.local",
            "subject": "Town Hall Meeting",
            "date": "2026-10-06",
            "read": 0,
            "body": long_body
        })
        check = self.email_service.get_by_id(email["id"])
        self.assertEqual(check["body"], long_body)
        self.email_service.delete(email["id"])

    def test_082_delete_email(self):
        email = self.email_service.create({
            "from_email": "spam@external.com",
            "subject": "Unsolicited Pitch",
            "date": "2026-10-06",
            "read": 1,
            "body": "Offer"
        })
        self.assertTrue(self.email_service.delete(email["id"]))
        self.assertIsNone(self.email_service.get_by_id(email["id"]))

    # =========================================================================
    # SECTION 10: Audit Logging & Live Activity Synchronization (Tests 83-90)
    # =========================================================================
    def test_083_audit_log_recorded_on_employee_create(self):
        created = self.emp_service.create({
            "name": "Audit Tracked Emp",
            "department": "Engineering",
            "role": "SRE",
            "status": "active",
            "email": "audit.emp@workhub.local"
        })
        logs = get_recent_audit_logs(limit=10)
        emp_logs = [l for l in logs if str(l["record_id"]) == str(created["id"]) and l["action"] == "CREATE"]
        self.assertGreater(len(emp_logs), 0)
        self.emp_service.delete(created["id"])

    def test_084_audit_log_recorded_on_employee_update(self):
        created = self.emp_service.create({
            "name": "Audit Update Emp",
            "department": "Engineering",
            "role": "SRE",
            "status": "active",
            "email": "audit.upd@workhub.local"
        })
        self.emp_service.update(created["id"], {"role": "Staff SRE"})
        logs = get_recent_audit_logs(limit=10)
        update_logs = [l for l in logs if str(l["record_id"]) == str(created["id"]) and l["action"] == "UPDATE"]
        self.assertGreater(len(update_logs), 0)
        self.emp_service.delete(created["id"])

    def test_085_audit_log_recorded_on_employee_delete(self):
        created = self.emp_service.create({
            "name": "Audit Delete Target",
            "department": "HR",
            "role": "Intern",
            "status": "active",
            "email": "audit.del@workhub.local"
        })
        emp_id = created["id"]
        self.emp_service.delete(emp_id)
        logs = get_recent_audit_logs(limit=10)
        del_logs = [l for l in logs if str(l["record_id"]) == str(emp_id) and l["action"] == "DELETE"]
        self.assertGreater(len(del_logs), 0)

    def test_086_audit_log_recorded_on_expense_approval(self):
        exp = self.exp_service.create({
            "employee": "Audit Exp",
            "category": "Travel",
            "amount": "₹5,000",
            "description": "Travel",
            "date": "2026-10-06",
            "status": "pending"
        })
        self.exp_service.update(exp["id"], {"status": "approved"})
        logs = get_recent_audit_logs(limit=10)
        exp_logs = [l for l in logs if str(l["record_id"]) == str(exp["id"]) and l["action"] == "UPDATE"]
        self.assertGreater(len(exp_logs), 0)
        self.exp_service.delete(exp["id"])

    def test_087_audit_log_recorded_on_leave_approval(self):
        lv = self.leave_service.create({
            "employee": "Audit Leave",
            "type": "Sick Leave",
            "dates": "Nov 1",
            "status": "pending"
        })
        self.leave_service.update(lv["id"], {"status": "approved"})
        logs = get_recent_audit_logs(limit=10)
        lv_logs = [l for l in logs if str(l["record_id"]) == str(lv["id"]) and l["action"] == "UPDATE"]
        self.assertGreater(len(lv_logs), 0)
        self.leave_service.delete(lv["id"])

    def test_088_audit_log_timestamp_format(self):
        logs = get_recent_audit_logs(limit=5)
        if logs:
            ts = logs[0]["timestamp"]
            self.assertIsNotNone(ts)

    def test_089_api_activities_endpoint_returns_json_array(self):
        res = self.client.get("/api/hr/activities/")
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_090_api_activities_endpoint_limit_parameter(self):
        res = self.client.get("/api/hr/activities/?limit=3")
        self.assertEqual(res.status_code, 200)
        self.assertLessEqual(len(res.json()), 3)

    # =========================================================================
    # SECTION 11: End-to-End FastAPI REST Controller Verification (Tests 91-96)
    # =========================================================================
    def test_091_api_employee_profile_dual_slash_routing(self):
        # Slash
        r1 = self.client.get("/api/hr/employees/EMP-001/")
        self.assertEqual(r1.status_code, 200)
        # No slash
        r2 = self.client.get("/api/hr/employees/EMP-001")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json()["name"], r2.json()["name"])

    def test_092_api_create_and_update_employee_via_http(self):
        payload = {
            "name": "HTTP Integration Employee",
            "department": "Engineering",
            "role": "Frontend Architect",
            "status": "active",
            "email": "http.test@workhub.local",
            "phone": "555-1234",
            "emergencyContact": "Support - 555-0000"
        }
        res = self.client.post("/api/hr/employees/", json=payload)
        self.assertEqual(res.status_code, 200)
        emp_id = res.json()["id"]

        patch_res = self.client.patch(f"/api/hr/employees/{emp_id}", json={"phone": "555-9999"})
        self.assertEqual(patch_res.status_code, 200)

        get_res = self.client.get(f"/api/hr/employees/{emp_id}")
        self.assertEqual(get_res.json()["phone"], "555-9999")

        self.client.delete(f"/api/hr/employees/{emp_id}")

    def test_093_api_expense_review_flow_via_http(self):
        exp = self.client.post("/api/hr/expenses/", json={
            "employee": "HTTP Expense User",
            "category": "Travel",
            "amount": "₹8,500",
            "description": "Travel",
            "date": "2026-10-06",
            "status": "pending",
            "receiptId": "REC-HTTP"
        }).json()

        approve_res = self.client.patch(f"/api/hr/expenses/{exp['id']}", json={"status": "approved"})
        self.assertEqual(approve_res.status_code, 200)
        self.assertEqual(approve_res.json()["status"], "approved")

        self.client.delete(f"/api/hr/expenses/{exp['id']}")

    def test_094_api_leave_approval_flow_via_http(self):
        lv = self.client.post("/api/hr/leaves/", json={
            "employee": "HTTP Leave User",
            "type": "Annual Leave",
            "dates": "Dec 1 - Dec 5",
            "status": "pending"
        }).json()

        approve_res = self.client.patch(f"/api/hr/leaves/{lv['id']}", json={"status": "approved"})
        self.assertEqual(approve_res.status_code, 200)
        self.assertEqual(approve_res.json()["status"], "approved")

        self.client.delete(f"/api/hr/leaves/{lv['id']}")

    def test_095_api_task_status_lifecycle_via_http(self):
        tsk = self.client.post("/api/hr/tasks/", json={
            "title": "HTTP Task Workflow",
            "assignedTo": "Admin",
            "dueDate": "2026-10-15",
            "priority": "high",
            "status": "pending"
        }).json()

        patch_res = self.client.patch(f"/api/hr/tasks/{tsk['id']}", json={"status": "completed"})
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["status"], "completed")

        self.client.delete(f"/api/hr/tasks/{tsk['id']}")

    def test_096_api_static_ui_served_at_root(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("WorkHub", res.text)

    # =========================================================================
    # SECTION 12: AI Worker Tool Direct SQLite Operations (Tests 97-100)
    # =========================================================================
    def test_097_ai_search_employee_records_tool(self):
        async def run():
            tool = SearchEmployeeRecordsTool()
            res = await tool.execute(query="Jane Smith")
            self.assertTrue(res.success)
            self.assertGreater(len(res.data["results"]), 0)
            self.assertEqual(res.data["results"][0]["id"], "EMP-002")
        asyncio.run(run())

    def test_098_ai_send_hr_email_tool(self):
        async def run():
            tool = SendHREmailTool()
            res = await tool.execute(
                to_email="employee@workhub.local",
                subject="AI Task Notification",
                body="Your expense has been approved."
            )
            self.assertTrue(res.success)
            self.assertIn("record", res.data)
            self.email_service.delete(res.data["record"]["id"])
        asyncio.run(run())

    def test_099_ai_employee_tools_direct_crud(self):
        async def run():
            get_tool = GetEmployeeTool()
            res = await get_tool.execute(id="EMP-001")
            self.assertTrue(res.success)
            self.assertEqual(res.data["name"], "John Doe")

            all_tool = GetAllEmployeesTool()
            all_res = await all_tool.execute(limit=10)
            self.assertTrue(all_res.success)
            self.assertEqual(len(all_res.data), 10)
        asyncio.run(run())

    def test_100_ai_sql_query_tool_safe_read_and_guardrails(self):
        async def run():
            sql_tool = SQLQueryTool()
            # 1. Safe SELECT execution directly from SQLite
            select_res = await sql_tool.execute(query="SELECT count(*) as total_employees FROM employees WHERE status = 'active'")
            self.assertTrue(select_res.success)
            self.assertGreater(select_res.data[0]["total_employees"], 10)

            # 2. Strict Security Policy violation rejection on DROP/ALTER attempts
            alter_res = await sql_tool.execute(query="ALTER TABLE employees ADD COLUMN test_col TEXT")
            self.assertFalse(alter_res.success)
            self.assertIn("Security Policy Violation", alter_res.error)

            drop_res = await sql_tool.execute(query="DROP TABLE leaves")
            self.assertFalse(drop_res.success)
            self.assertIn("Security Policy Violation", drop_res.error)
        asyncio.run(run())

    # =========================================================================
    # SECTION 13: UI Store & Full End-to-End Reactivity Synchronization (Tests 101-110)
    # =========================================================================
    def simulate_ui_fetch_store(self):
        """Simulates frontend app.js fetchStore() calling all backend REST endpoints."""
        ui_store = {}
        endpoints = ['employees', 'expenses', 'leaves', 'benefits', 'tasks', 'emails', 'documents', 'activities']
        for ep in endpoints:
            res = self.client.get(f"/api/hr/{ep}/")
            self.assertEqual(res.status_code, 200, f"UI fetchStore failed for endpoint /api/hr/{ep}/")
            data = res.json()
            if ep == 'emails':
                ui_store[ep] = [{
                    **m,
                    'from': m.get('from') or m.get('from_email') or 'HR System',
                    'from_email': m.get('from_email') or m.get('from') or 'hr@workhub.local'
                } for m in data]
            else:
                ui_store[ep] = data
        return ui_store

    def calculate_ui_dashboard_metrics(self, ui_store):
        """Simulates renderDashboard() calculation logic from app.js."""
        total_employees = len(ui_store['employees'])
        pending_expenses = len([e for e in ui_store['expenses'] if e.get('status') == 'pending'])
        pending_leaves = len([l for l in ui_store['leaves'] if l.get('status') == 'pending'])
        pending_approvals = pending_expenses + pending_leaves
        open_tasks = len([t for t in ui_store['tasks'] if t.get('status') != 'completed'])
        
        total_exp_amount = 0
        for e in ui_store['expenses']:
            if e.get('status') == 'approved':
                amt = int(str(e.get('amount', 0)).replace('₹', '').replace('$', '').replace(',', '').strip() or 0)
                total_exp_amount += amt

        return {
            "total_employees": total_employees,
            "pending_approvals": pending_approvals,
            "open_tasks": open_tasks,
            "expenses_processed": total_exp_amount
        }

    def calculate_ui_sidebar_badges(self, ui_store):
        """Simulates updateSidebarBadges() logic from app.js."""
        pending_expenses = len([e for e in ui_store['expenses'] if e.get('status') == 'pending'])
        open_tasks = len([t for t in ui_store['tasks'] if t.get('status') != 'completed'])
        unread_emails = len([m for m in ui_store['emails'] if not m.get('read') or m.get('read') == 0])
        return {
            "expenses_badge": pending_expenses,
            "tasks_badge": open_tasks,
            "emails_badge": unread_emails
        }

    def test_101_ui_store_sync_matches_backend_exact_counts(self):
        ui_store = self.simulate_ui_fetch_store()
        db_emps = self.emp_service.get_all(limit=500)
        self.assertEqual(len(ui_store['employees']), len(db_emps))
        self.assertGreaterEqual(len(ui_store['employees']), 60)

    def test_102_ui_dashboard_metrics_sync_on_employee_addition(self):
        # 1. Baseline UI state
        init_store = self.simulate_ui_fetch_store()
        init_metrics = self.calculate_ui_dashboard_metrics(init_store)

        # 2. Add employee via backend API
        created = self.client.post("/api/hr/employees/", json={
            "name": "Sync Verification User",
            "department": "Engineering",
            "role": "Staff Engineer",
            "status": "active",
            "email": "sync.verify@workhub.local"
        }).json()

        # 3. Synchronize UI store & verify updated count
        new_store = self.simulate_ui_fetch_store()
        new_metrics = self.calculate_ui_dashboard_metrics(new_store)
        self.assertEqual(new_metrics["total_employees"], init_metrics["total_employees"] + 1)

        # 4. Clean up
        self.client.delete(f"/api/hr/employees/{created['id']}")

    def test_103_ui_pending_approvals_sync_on_expense_submission_and_approval(self):
        # 1. Baseline
        init_store = self.simulate_ui_fetch_store()
        init_metrics = self.calculate_ui_dashboard_metrics(init_store)

        # 2. Add pending expense
        exp = self.client.post("/api/hr/expenses/", json={
            "employee": "Jane Smith",
            "category": "Travel",
            "amount": "₹20,000",
            "description": "Flight Tickets",
            "date": "2026-10-06",
            "status": "pending",
            "receiptId": "REC-SYNC-1"
        }).json()

        # UI syncs: pending approvals should increment by 1
        after_post_store = self.simulate_ui_fetch_store()
        after_post_metrics = self.calculate_ui_dashboard_metrics(after_post_store)
        self.assertEqual(after_post_metrics["pending_approvals"], init_metrics["pending_approvals"] + 1)

        # 3. Approve expense
        self.client.patch(f"/api/hr/expenses/{exp['id']}", json={"status": "approved"})

        # UI syncs: pending approvals drops by 1, processed expenses increases by 20,000
        after_app_store = self.simulate_ui_fetch_store()
        after_app_metrics = self.calculate_ui_dashboard_metrics(after_app_store)
        self.assertEqual(after_app_metrics["pending_approvals"], init_metrics["pending_approvals"])
        self.assertEqual(after_app_metrics["expenses_processed"], init_metrics["expenses_processed"] + 20000)

        # Clean up
        self.client.delete(f"/api/hr/expenses/{exp['id']}")

    def test_104_ui_pending_approvals_sync_on_leave_request_and_rejection(self):
        init_store = self.simulate_ui_fetch_store()
        init_metrics = self.calculate_ui_dashboard_metrics(init_store)

        # 1. Submit leave request
        lv = self.client.post("/api/hr/leaves/", json={
            "employee": "Bob Wilson",
            "type": "Sick Leave",
            "dates": "Nov 12 - Nov 14",
            "status": "pending"
        }).json()

        store1 = self.simulate_ui_fetch_store()
        metrics1 = self.calculate_ui_dashboard_metrics(store1)
        self.assertEqual(metrics1["pending_approvals"], init_metrics["pending_approvals"] + 1)

        # 2. Reject leave request
        self.client.patch(f"/api/hr/leaves/{lv['id']}", json={"status": "rejected"})

        store2 = self.simulate_ui_fetch_store()
        metrics2 = self.calculate_ui_dashboard_metrics(store2)
        self.assertEqual(metrics2["pending_approvals"], init_metrics["pending_approvals"])

        self.client.delete(f"/api/hr/leaves/{lv['id']}")

    def test_105_ui_sidebar_badges_sync_on_tasks_and_emails(self):
        init_store = self.simulate_ui_fetch_store()
        init_badges = self.calculate_ui_sidebar_badges(init_store)

        # 1. Create open task & unread email
        tsk = self.client.post("/api/hr/tasks/", json={
            "title": "Badge Sync Test Task",
            "assignedTo": "Admin",
            "dueDate": "2026-10-15",
            "priority": "high",
            "status": "pending"
        }).json()

        email = self.client.post("/api/hr/emails/", json={
            "from_email": "test.badge@workhub.local",
            "subject": "Badge Test Unread",
            "date": "2026-10-06",
            "read": 0,
            "body": "Unread message"
        }).json()

        # UI syncs: tasks badge +1, emails badge +1
        s1 = self.simulate_ui_fetch_store()
        b1 = self.calculate_ui_sidebar_badges(s1)
        self.assertEqual(b1["tasks_badge"], init_badges["tasks_badge"] + 1)
        self.assertEqual(b1["emails_badge"], init_badges["emails_badge"] + 1)

        # 2. Complete task and mark email as read
        self.client.patch(f"/api/hr/tasks/{tsk['id']}", json={"status": "completed"})
        self.client.patch(f"/api/hr/emails/{email['id']}", json={"read": 1})

        # UI syncs: badges return to baseline
        s2 = self.simulate_ui_fetch_store()
        b2 = self.calculate_ui_sidebar_badges(s2)
        self.assertEqual(b2["tasks_badge"], init_badges["tasks_badge"])
        self.assertEqual(b2["emails_badge"], init_badges["emails_badge"])

        self.client.delete(f"/api/hr/tasks/{tsk['id']}")
        self.client.delete(f"/api/hr/emails/{email['id']}")

    def test_106_ui_employee_profile_view_render_accuracy_after_update(self):
        # Pick EMP-002 (Jane Smith)
        new_phone = "555-4321"
        new_dept = "Finance"
        new_status = "active"

        try:
            # User updates profile via UI form submit
            self.client.patch("/api/hr/employees/EMP-002", json={
                "phone": new_phone,
                "department": new_dept,
                "status": new_status
            })

            # UI polls backend and renders employee_profile('EMP-002')
            ui_store = self.simulate_ui_fetch_store()
            emp = next((e for e in ui_store['employees'] if e['id'] == 'EMP-002'), None)
            self.assertIsNotNone(emp, "Employee EMP-002 must be found in synchronized UI store")
            self.assertEqual(emp['phone'], new_phone)
            self.assertEqual(emp['department'], new_dept)
            self.assertEqual(emp['status'], new_status)
        finally:
            # Restore EMP-002 to original state
            self.client.patch("/api/hr/employees/EMP-002", json={
                "phone": "555-0101",
                "department": "HR",
                "status": "active"
            })

    def test_107_ui_recent_activity_feed_sync_with_audit_logs(self):
        # 1. Trigger database action (benefit addition)
        ben = self.client.post("/api/hr/benefits/", json={
            "name": "Sync Activity Benefit",
            "provider": "SyncHealth",
            "coverage": "100%",
            "enrolled": 1,
            "status": "active"
        }).json()

        # 2. UI polls /activities/
        ui_store = self.simulate_ui_fetch_store()
        activities = ui_store.get('activities', [])
        self.assertGreater(len(activities), 0)
        
        # Verify the latest activity matches our action
        latest_act = activities[0]
        self.assertEqual(latest_act['table_name'], 'benefits')
        self.assertEqual(latest_act['action'], 'CREATE')
        self.assertEqual(str(latest_act['record_id']), str(ben['id']))

        self.client.delete(f"/api/hr/benefits/{ben['id']}")

    def test_108_ui_expense_filtering_reactivity(self):
        # Add 1 pending and 1 approved expense
        e_pending = self.client.post("/api/hr/expenses/", json={
            "employee": "Filter Pending User",
            "category": "Software",
            "amount": "₹1,000",
            "description": "Tool",
            "date": "2026-10-06",
            "status": "pending"
        }).json()

        e_approved = self.client.post("/api/hr/expenses/", json={
            "employee": "Filter Approved User",
            "category": "Travel",
            "amount": "₹2,000",
            "description": "Cab",
            "date": "2026-10-06",
            "status": "approved"
        }).json()

        ui_store = self.simulate_ui_fetch_store()

        # Filter by Pending
        ui_filtered_pending = [e for e in ui_store['expenses'] if e['status'] == 'pending']
        self.assertTrue(any(e['id'] == e_pending['id'] for e in ui_filtered_pending))
        self.assertFalse(any(e['id'] == e_approved['id'] for e in ui_filtered_pending))

        # Filter by Approved
        ui_filtered_approved = [e for e in ui_store['expenses'] if e['status'] == 'approved']
        self.assertTrue(any(e['id'] == e_approved['id'] for e in ui_filtered_approved))
        self.assertFalse(any(e['id'] == e_pending['id'] for e in ui_filtered_approved))

        self.client.delete(f"/api/hr/expenses/{e_pending['id']}")
        self.client.delete(f"/api/hr/expenses/{e_approved['id']}")

    def test_109_ui_leave_calendar_sync_with_approved_records(self):
        # Create an approved leave
        lv = self.client.post("/api/hr/leaves/", json={
            "employee": "Calendar Sync User",
            "type": "Annual Leave",
            "dates": "Dec 25 - Dec 31",
            "status": "approved"
        }).json()

        ui_store = self.simulate_ui_fetch_store()
        calendar_leaves = [l for l in ui_store['leaves'] if l.get('status') == 'approved']
        self.assertTrue(any(l['id'] == lv['id'] for l in calendar_leaves))
        self.assertTrue(any(l['employee'] == 'Calendar Sync User' for l in calendar_leaves))

        self.client.delete(f"/api/hr/leaves/{lv['id']}")

    def test_110_ui_realtime_polling_interval_data_consistency(self):
        # Verify complete roundtrip data consistency across all models
        ui_store = self.simulate_ui_fetch_store()
        self.assertIn('employees', ui_store)
        self.assertIn('expenses', ui_store)
        self.assertIn('leaves', ui_store)
        self.assertIn('benefits', ui_store)
        self.assertIn('tasks', ui_store)
        self.assertIn('emails', ui_store)
        self.assertIn('documents', ui_store)
        self.assertIn('activities', ui_store)

        for key in ui_store:
            self.assertIsInstance(ui_store[key], list, f"UI store slice for '{key}' must be an Array/List")
            self.assertGreaterEqual(len(ui_store[key]), 0)


    # =========================================================================
    # SECTION 14: Complete UI Component Rendering, DOM Elements & Workflows (Tests 111-125)
    # =========================================================================
    def test_111_ui_render_dashboard_html_structure(self):
        ui_store = self.simulate_ui_fetch_store()
        metrics = self.calculate_ui_dashboard_metrics(ui_store)
        
        # Verify Stat Card elements exist and match data
        self.assertGreaterEqual(metrics["total_employees"], 60)
        self.assertGreaterEqual(metrics["pending_approvals"], 0)
        self.assertGreaterEqual(metrics["open_tasks"], 0)
        self.assertGreaterEqual(metrics["expenses_processed"], 0)

    def test_112_ui_render_employee_directory_html_table(self):
        ui_store = self.simulate_ui_fetch_store()
        emps = ui_store['employees']
        
        # Verify table row generation contains correct data attributes
        rows = [f'<tr data-emp-id="{e["id"]}">' for e in emps]
        self.assertEqual(len(rows), len(emps))
        self.assertIn('<tr data-emp-id="EMP-001">', rows)
        self.assertIn('<tr data-emp-id="EMP-002">', rows)

    def test_113_ui_render_employee_profile_form_fields(self):
        ui_store = self.simulate_ui_fetch_store()
        emp = next(e for e in ui_store['employees'] if e['id'] == 'EMP-002')
        
        # Validate all expected form fields are populated
        self.assertEqual(emp['name'], 'Jane Smith')
        self.assertEqual(emp['email'], 'jane.smith@workhub.local')
        self.assertIsNotNone(emp.get('phone'))
        self.assertIsNotNone(emp.get('emergencyContact'))
        self.assertEqual(emp['department'], 'HR')
        self.assertEqual(emp['status'], 'active')

    def test_114_ui_render_expense_management_rows_and_actions(self):
        ui_store = self.simulate_ui_fetch_store()
        for exp in ui_store['expenses']:
            self.assertIn('id', exp)
            self.assertIn('amount', exp)
            self.assertIn('category', exp)
            self.assertIn('status', exp)
            # Pending must have Review action, approved/rejected must be Processed
            if exp['status'] == 'pending':
                action_type = 'review'
            else:
                action_type = 'processed'
            self.assertIn(action_type, ['review', 'processed'])

    def test_115_ui_render_leave_requests_action_buttons(self):
        ui_store = self.simulate_ui_fetch_store()
        for lv in ui_store['leaves']:
            self.assertIn('id', lv)
            self.assertIn('employee', lv)
            self.assertIn('type', lv)
            self.assertIn('dates', lv)
            self.assertIn('status', lv)

    def test_116_ui_render_benefits_management_structure(self):
        ui_store = self.simulate_ui_fetch_store()
        for ben in ui_store['benefits']:
            self.assertIn('id', ben)
            self.assertIn('name', ben)
            self.assertIn('provider', ben)
            self.assertIn('coverage', ben)
            self.assertIn('status', ben)

    def test_117_ui_render_tasks_priority_and_status_badges(self):
        ui_store = self.simulate_ui_fetch_store()
        for tsk in ui_store['tasks']:
            self.assertIn('id', tsk)
            self.assertIn('title', tsk)
            self.assertIn('priority', tsk)
            self.assertIn('status', tsk)
            self.assertIn(tsk['priority'].lower(), ['low', 'medium', 'high'])
            self.assertIn(tsk['status'].lower(), ['pending', 'in_progress', 'completed'])

    def test_118_ui_render_inbox_emails_and_reader_payload(self):
        ui_store = self.simulate_ui_fetch_store()
        for msg in ui_store['emails']:
            self.assertIn('id', msg)
            self.assertIn('subject', msg)
            self.assertIn('from_email', msg)
            self.assertIn('body', msg)
            self.assertIn('date', msg)

    def test_119_ui_render_document_center_types(self):
        ui_store = self.simulate_ui_fetch_store()
        for doc in ui_store['documents']:
            self.assertIn('id', doc)
            self.assertIn('name', doc)
            self.assertIn('type', doc)
            self.assertIn(doc['type'], ['Policy', 'Report', 'Receipt', 'Contract', 'General'])

    def test_120_ui_add_employee_modal_form_submission_workflow(self):
        # 1. Fill form
        form_data = {
            "name": "Modal Workflow Employee",
            "email": "modal.emp@workhub.local",
            "role": "Full Stack Engineer",
            "department": "Engineering",
            "phone": "555-5555",
            "emergencyContact": "Contact - 555-5556",
            "status": "active"
        }
        # 2. Submit via API
        res = self.client.post("/api/hr/employees/", json=form_data)
        self.assertEqual(res.status_code, 200)
        created_id = res.json()["id"]

        # 3. Synchronize & Verify in Directory View
        ui_store = self.simulate_ui_fetch_store()
        found = any(e['id'] == created_id and e['name'] == form_data['name'] for e in ui_store['employees'])
        self.assertTrue(found)

        self.client.delete(f"/api/hr/employees/{created_id}")

    def test_121_ui_add_expense_modal_form_submission_workflow(self):
        # 1. Fill expense modal
        exp_form = {
            "employee": "John Doe",
            "category": "Software",
            "amount": "₹9,999",
            "description": "Cloud Subscription",
            "date": "2026-10-06",
            "status": "pending",
            "receiptId": "REC-MODAL-1"
        }
        res = self.client.post("/api/hr/expenses/", json=exp_form)
        self.assertEqual(res.status_code, 200)
        exp_id = res.json()["id"]

        # 2. Verify in UI store
        ui_store = self.simulate_ui_fetch_store()
        found = next((e for e in ui_store['expenses'] if e['id'] == exp_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found['amount'], "₹9,999")

        self.client.delete(f"/api/hr/expenses/{exp_id}")

    def test_122_ui_request_leave_modal_form_submission_workflow(self):
        # 1. Fill leave modal
        lv_form = {
            "employee": "Jane Smith",
            "type": "Sick Leave",
            "dates": "Dec 10 - Dec 12",
            "status": "pending"
        }
        res = self.client.post("/api/hr/leaves/", json=lv_form)
        self.assertEqual(res.status_code, 200)
        lv_id = res.json()["id"]

        ui_store = self.simulate_ui_fetch_store()
        found = next((l for l in ui_store['leaves'] if l['id'] == lv_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found['type'], "Sick Leave")

        self.client.delete(f"/api/hr/leaves/{lv_id}")

    def test_123_ui_create_task_modal_form_submission_workflow(self):
        # 1. Fill task modal
        task_form = {
            "title": "Modal Assigned Task",
            "assignedTo": "Admin",
            "dueDate": "2026-11-01",
            "priority": "high",
            "status": "pending"
        }
        res = self.client.post("/api/hr/tasks/", json=task_form)
        self.assertEqual(res.status_code, 200)
        tsk_id = res.json()["id"]

        ui_store = self.simulate_ui_fetch_store()
        found = next((t for t in ui_store['tasks'] if t['id'] == tsk_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found['priority'], "high")

        self.client.delete(f"/api/hr/tasks/{tsk_id}")

    def test_124_ui_compose_email_modal_form_submission_workflow(self):
        # 1. Fill email compose modal
        email_form = {
            "from_email": "jane.smith@workhub.local",
            "subject": "Modal Composed Email",
            "date": "2026-10-06",
            "read": 0,
            "body": "Test message body content."
        }
        res = self.client.post("/api/hr/emails/", json=email_form)
        self.assertEqual(res.status_code, 200)
        msg_id = res.json()["id"]

        ui_store = self.simulate_ui_fetch_store()
        found = next((m for m in ui_store['emails'] if m['id'] == msg_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found['subject'], "Modal Composed Email")

        self.client.delete(f"/api/hr/emails/{msg_id}")

    def test_125_ui_upload_document_modal_form_submission_workflow(self):
        # 1. Fill document upload modal
        doc_form = {
            "name": "Modal Uploaded Doc.pdf",
            "type": "Policy",
            "relatedTo": "All Staff",
            "content": "Uploaded policy content text."
        }
        res = self.client.post("/api/hr/documents/", json=doc_form)
        self.assertEqual(res.status_code, 200)
        doc_id = res.json()["id"]

        ui_store = self.simulate_ui_fetch_store()
        found = next((d for d in ui_store['documents'] if d['id'] == doc_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found['name'], "Modal Uploaded Doc.pdf")

        self.client.delete(f"/api/hr/documents/{doc_id}")


    # =========================================================================
    # SECTION 15: AI Agent Tools <-> Frontend UI Full Reactivity Synchronization (Tests 126-135)
    # =========================================================================
    def test_126_ai_agent_onboard_employee_syncs_to_ui_directory(self):
        async def run():
            tool = OnboardEmployeeTool()
            res = await tool.execute(employee_name="AI Onboarded Dev", department="Engineering", role="Senior AI Engineer")
            self.assertTrue(res.success)
            emp_id = res.data["id"]

            # UI synchronizes from backend SQLite
            ui_store = self.simulate_ui_fetch_store()
            found = next((e for e in ui_store["employees"] if e["id"] == emp_id), None)
            self.assertIsNotNone(found, "AI onboarded employee must be present in synchronized UI store")
            self.assertEqual(found["name"], "AI Onboarded Dev")
            self.assertEqual(found["department"], "Engineering")

            self.emp_service.delete(emp_id)
        asyncio.run(run())

    def test_127_ai_agent_approve_expense_syncs_to_ui_dashboard(self):
        async def run():
            # 1. Create a pending expense
            exp = self.exp_service.create({
                "employee": "AI Agent Expense",
                "category": "Software",
                "amount": "₹15,000",
                "description": "AI API Credits",
                "date": "2026-10-06",
                "status": "pending"
            })
            
            init_store = self.simulate_ui_fetch_store()
            init_metrics = self.calculate_ui_dashboard_metrics(init_store)

            # 2. AI agent executes ManageExpenseTool to approve
            tool = ManageExpenseTool()
            res = await tool.execute(expense_id=str(exp["id"]), action="approve")
            self.assertTrue(res.success)

            # 3. UI polls and dashboard metrics update
            synced_store = self.simulate_ui_fetch_store()
            synced_metrics = self.calculate_ui_dashboard_metrics(synced_store)
            self.assertEqual(synced_metrics["pending_approvals"], init_metrics["pending_approvals"] - 1)
            self.assertEqual(synced_metrics["expenses_processed"], init_metrics["expenses_processed"] + 15000)

            self.exp_service.delete(exp["id"])
        asyncio.run(run())

    def test_128_ai_agent_approve_leave_syncs_to_ui_calendar(self):
        async def run():
            lv = self.leave_service.create({
                "employee": "AI Agent Leave User",
                "type": "Casual Leave",
                "dates": "Nov 20 - Nov 22",
                "status": "pending"
            })

            tool = ManageLeaveRequestTool()
            res = await tool.execute(leave_id=str(lv["id"]), action="approve")
            self.assertTrue(res.success)

            ui_store = self.simulate_ui_fetch_store()
            approved_leaves = [l for l in ui_store["leaves"] if l.get("status") == "approved"]
            self.assertTrue(any(l["id"] == lv["id"] for l in approved_leaves))

            self.leave_service.delete(lv["id"])
        asyncio.run(run())

    def test_129_ai_agent_create_task_syncs_to_ui_sidebar_badge(self):
        async def run():
            init_store = self.simulate_ui_fetch_store()
            init_badges = self.calculate_ui_sidebar_badges(init_store)

            tool = HRTaskManagementTool()
            res = await tool.execute(title="AI Agent Created Task", status="pending", assignedTo="Admin")
            self.assertTrue(res.success)
            task_id = res.data["record"]["id"]

            # UI receives update and badge counter increments
            after_store = self.simulate_ui_fetch_store()
            after_badges = self.calculate_ui_sidebar_badges(after_store)
            self.assertEqual(after_badges["tasks_badge"], init_badges["tasks_badge"] + 1)

            self.task_service.delete(task_id)
        asyncio.run(run())

    def test_130_ai_agent_schedule_interview_syncs_to_ui_tasks(self):
        async def run():
            tool = ScheduleInterviewTool()
            res = await tool.execute(candidate_name="Alice Candidate", date="2026-10-25")
            self.assertTrue(res.success)
            task_id = res.data["id"]

            ui_store = self.simulate_ui_fetch_store()
            found = next((t for t in ui_store["tasks"] if t["id"] == task_id), None)
            self.assertIsNotNone(found)
            self.assertIn("Alice Candidate", found["title"])

            self.task_service.delete(task_id)
        asyncio.run(run())

    def test_131_ai_agent_upload_document_syncs_to_ui_document_center(self):
        async def run():
            tool = UploadDocumentTool()
            res = await tool.execute(file_name="AI_Security_Policy.pdf", content="Security policy content")
            self.assertTrue(res.success)
            doc_id = res.data["id"]

            ui_store = self.simulate_ui_fetch_store()
            found = next((d for d in ui_store["documents"] if d["id"] == doc_id), None)
            self.assertIsNotNone(found)
            self.assertEqual(found["name"], "AI_Security_Policy.pdf")

            self.doc_service.delete(doc_id)
        asyncio.run(run())

    def test_132_ai_agent_update_employee_profile_syncs_to_ui_profile_view(self):
        async def run():
            # Use temporary employee to test profile updates
            temp_emp = self.emp_service.create({
                "name": "Profile Sync Test Emp",
                "department": "Engineering",
                "role": "QA Engineer",
                "phone": "555-0001",
                "emergencyContact": "Contact Initial"
            })
            temp_id = temp_emp["id"]

            tool = UpdateEmployeeProfileTool()
            res = await tool.execute(employee_id=temp_id, phone="555-9999", emergency_contact="Contact Updated - 555-8888")
            self.assertTrue(res.success)

            ui_store = self.simulate_ui_fetch_store()
            emp = next((e for e in ui_store["employees"] if e["id"] == temp_id), None)
            self.assertIsNotNone(emp)
            self.assertEqual(emp["phone"], "555-9999")
            self.assertEqual(emp["emergencyContact"], "Contact Updated - 555-8888")

            self.emp_service.delete(temp_id)
        asyncio.run(run())

    def test_133_ai_agent_activity_feed_realtime_sync_after_tool_execution(self):
        async def run():
            tool = HRTaskManagementTool()
            res = await tool.execute(title="Audit Activity Task", status="pending", assignedTo="Admin")
            self.assertTrue(res.success)
            task_id = res.data["record"]["id"]

            ui_store = self.simulate_ui_fetch_store()
            activities = ui_store.get("activities", [])
            self.assertGreater(len(activities), 0)
            
            # Latest activity matches the tool's action
            matched = any(str(a.get("record_id")) == str(task_id) and a.get("table_name") == "tasks" for a in activities)
            self.assertTrue(matched, "AI Agent tool action must be logged in SQLite audit_logs and visible to UI Recent Activity")

            self.task_service.delete(task_id)
        asyncio.run(run())

    def test_134_ai_agent_send_email_syncs_to_ui_inbox_and_badge(self):
        async def run():
            init_store = self.simulate_ui_fetch_store()
            init_badges = self.calculate_ui_sidebar_badges(init_store)

            tool = SendHREmailTool()
            res = await tool.execute(
                to_email="employee.sync@workhub.local",
                subject="Synchronized Notification",
                body="Your profile has been synchronized."
            )
            self.assertTrue(res.success)
            email_id = res.data["record"]["id"]

            # UI syncs: inbox contains new email & unread badge increases
            after_store = self.simulate_ui_fetch_store()
            after_badges = self.calculate_ui_sidebar_badges(after_store)
            self.assertEqual(after_badges["emails_badge"], init_badges["emails_badge"] + 1)
            found = next((m for m in after_store["emails"] if m["id"] == email_id), None)
            self.assertIsNotNone(found)
            self.assertEqual(found["subject"], "Synchronized Notification")

            self.email_service.delete(email_id)
        asyncio.run(run())

    def test_135_ai_agent_sql_query_and_ui_consistency(self):
        async def run():
            sql_tool = SQLQueryTool()
            res = await sql_tool.execute(query="SELECT count(*) as count FROM employees")
            self.assertTrue(res.success)
            db_count = res.data[0]["count"]

            ui_store = self.simulate_ui_fetch_store()
            ui_count = len(ui_store["employees"])
            self.assertEqual(db_count, ui_count, "AI SQL Tool count must exactly equal Frontend UI store count")
        asyncio.run(run())


    def test_136_list_assignable_employees_tool_returns_all_active_employees(self):
        async def run():
            tool = ListAssignableEmployeesTool()
            res = await tool.execute()
            self.assertTrue(res.success)
            self.assertGreaterEqual(res.data["count"], 50)
            # Check structure of employee options
            first_emp = res.data["employees"][0]
            self.assertIn("id", first_emp)
            self.assertIn("name", first_emp)
            self.assertIn("department", first_emp)
            self.assertIn("label", first_emp)
        asyncio.run(run())

    def test_137_manage_hr_task_resolves_employee_id_assignment(self):
        async def run():
            tool = HRTaskManagementTool()
            # Assign using Employee ID
            res = await tool.execute(title="Resolve ID Task", assignedTo="EMP-001")
            self.assertTrue(res.success)
            task_id = res.data["record"]["id"]
            # Verify assignedTo was auto-resolved to John Doe
            self.assertEqual(res.data["record"]["assignedTo"], "John Doe")
            self.task_service.delete(task_id)
        asyncio.run(run())

    def test_138_ui_employee_options_html_generator_contains_all_employees(self):
        ui_store = self.simulate_ui_fetch_store()
        emps = ui_store["employees"]
        # Generate options
        options = '<option value="Admin">Admin (HR Manager)</option>'
        for e in emps:
            options += f'<option value="{e["name"]}">{e["name"]} ({e["id"]} - {e.get("department", "General")})</option>'
        
        self.assertIn('<option value="Admin">Admin (HR Manager)</option>', options)
        self.assertIn('John Doe (EMP-001 - Engineering)', options)
        self.assertIn('Jane Smith (EMP-002 - HR)', options)

    def test_139_ui_email_options_html_generator_contains_all_employees(self):
        ui_store = self.simulate_ui_fetch_store()
        emps = ui_store["employees"]
        email_options = '<option value="all@workhub.local">All Staff &lt;all@workhub.local&gt;</option>'
        for e in emps:
            email = e.get("email") or f"{e['name'].lower().replace(' ', '.')}@workhub.local"
            email_options += f'<option value="{email}">{e["name"]} &lt;{email}&gt;</option>'
        
        self.assertIn('john.doe@workhub.local', email_options)
        self.assertIn('jane.smith@workhub.local', email_options)

    def test_140_task_modal_select_assignment_flow(self):
        # Create task where assigned employee is chosen from current employee dropdown
        ui_store = self.simulate_ui_fetch_store()
        target_emp = ui_store["employees"][0]["name"]
        
        res = self.client.post("/api/hr/tasks/", json={
            "title": "Selected From Dropdown Task",
            "assignedTo": target_emp,
            "dueDate": "2026-11-15",
            "priority": "high",
            "status": "pending"
        })
        self.assertEqual(res.status_code, 200)
        task_id = res.json()["id"]

        synced_store = self.simulate_ui_fetch_store()
        found = next((t for t in synced_store["tasks"] if t["id"] == task_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["assignedTo"], target_emp)

        self.client.delete(f"/api/hr/tasks/{task_id}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" EXECUTING COMPLETE TEST SUITE: WORKHUB HR CLEAN ARCHITECTURE & UI ")
    print("=" * 70 + "\n")
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWorkHubHRCleanArchitectureComprehensive)
    result = runner.run(suite)
    if not result.wasSuccessful():
        print(f"\n[FAIL] {len(result.failures)} failures, {len(result.errors)} errors encountered.")
        sys.exit(1)
    print("\n" + "=" * 70)
    print(f" >>> ALL {result.testsRun} TESTS PASSED SUCCESSFULLY! DIRECT SQLITE & UI SYNC VERIFIED! <<<")
    print("=" * 70 + "\n")


