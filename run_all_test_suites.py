"""
========================================================================================
 WORKHUB AI TASK WORKER: MASTER TEST SUITE CONTROLLER
========================================================================================
File Path: run_all_test_suites.py

Master test runner orchestrating all three major verification test suites:
  [1] Web Automation & Self-Healing Recovery Suite (8 Test Cases)
  [2] Multi-Step Complex Agentic Audit Suite       (4 Test Cases)
  [3] Database CRUD & Human-in-the-Loop Safety Suite (4 Test Cases)

Usage:
  python run_all_test_suites.py             # Interactive Menu
  python run_all_test_suites.py web         # Run Web Automation Suite
  python run_all_test_suites.py audit       # Run Complex Audit Suite
  python run_all_test_suites.py crud        # Run Database CRUD Suite
  python run_all_test_suites.py all         # Run All Suites End-to-End
========================================================================================
"""

import os
import sys
import asyncio
import subprocess

# Ensure UTF-8 clean output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SUITES = {
    "1": {
        "key": "scenarios",
        "title": "WorkHub Web 20-Scenario Production Suite (20 Scenarios)",
        "file": "test_workhub_web_suite.py",
        "description": "20 realistic production browser scenarios (Create/edit employee, leaves, expenses, tasks, upload_file, validation/stale recovery, checkpoint resume)."
    },
    "2": {
        "key": "web",
        "title": "Web Automation & Recovery Layer Suite (8 Test Cases)",
        "file": "test_web_automation_suite.py",
        "description": "Playwright browser automation, 9-tier auto-healing, watchdog, intelligent wait, dual-layer verification, and stuck recovery."
    },
    "3": {
        "key": "audit",
        "title": "Multi-Step Complex Agentic Audit Suite (4 Test Cases)",
        "file": "test_complex_tasks_suite.py",
        "description": "Multi-step corporate audits (headcount, expenses, leave overlaps, task priority) with LLM reasoning and SQL execution."
    },
    "4": {
        "key": "crud",
        "title": "Database CRUD & Human-in-the-Loop Safety Suite (4 Test Cases)",
        "file": "test_database_crud_suite.py",
        "description": "Live SQLite mutations, employee queries, task creation, expense approval, and rich HITL authorization context verification."
    }
}


def run_test_file(filename: str, task_arg: str = "all"):
    print("\n" + "#" * 85)
    print(f"   LAUNCHING SUITE: {filename.upper()} (Target: {task_arg})   ".center(85))
    print("#" * 85 + "\n")
    
    cmd = [sys.executable, filename, str(task_arg)]
    subprocess.run(cmd)


def main():
    print("\n" + "=" * 85)
    print("        WORKHUB AI TASK WORKER: MASTER TEST SUITE CONTROLLER        ".center(85))
    print("=" * 85)

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower().strip()
        if arg in ["1", "web", "browser"]:
            run_test_file("test_web_automation_suite.py", sys.argv[2] if len(sys.argv) > 2 else "all")
            return
        elif arg in ["2", "audit", "complex"]:
            run_test_file("test_complex_tasks_suite.py", sys.argv[2] if len(sys.argv) > 2 else "all")
            return
        elif arg in ["3", "crud", "database"]:
            run_test_file("test_database_crud_suite.py", sys.argv[2] if len(sys.argv) > 2 else "all")
            return
        elif arg in ["all", "a"]:
            for k in ["1", "2", "3"]:
                run_test_file(SUITES[k]["file"], "all")
            return

    print("\nPlease select a test suite to run:\n")
    for k, s in SUITES.items():
        print(f"  [{k}] {s['title']}")
        print(f"      └─ {s['description']}\n")
    print("  [A] Run All 3 Suites End-to-End (16 Total Test Cases)")
    print("  [Q] Quit\n")

    try:
        choice = input("Enter choice (1, 2, 3, A, or Q) [Default: 1]: ").strip().lower()
        if choice in ["q", "quit", "exit"]:
            print("Exiting.")
            return
        elif choice in ["1", "web", "browser", ""]:
            run_test_file(SUITES["1"]["file"], "all")
        elif choice in ["2", "audit", "complex"]:
            run_test_file(SUITES["2"]["file"], "all")
        elif choice in ["3", "crud", "database"]:
            run_test_file(SUITES["3"]["file"], "all")
        elif choice in ["a", "all"]:
            for k in ["1", "2", "3"]:
                run_test_file(SUITES[k]["file"], "all")
        else:
            print("Invalid selection.")
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")


if __name__ == "__main__":
    main()
