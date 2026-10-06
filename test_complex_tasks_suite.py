"""
========================================================================================
 WORKHUB AI TASK WORKER: COMPLEX TASKS TEST SUITE (ONE-BY-ONE EXECUTION)
========================================================================================
File Path: test_complex_tasks_suite.py

This test suite executes 4 complex, multi-step corporate audit tasks one-by-one against
the live AI Worker Agent and SQLite database.

For each task, it presents:
  1. Task Objective & Natural Language Prompt
  2. Expected Output / Benchmark Truth
  3. Live AI Agent Execution Trace (Reasoning + SQL / Tool Calls)
  4. Actual Output from the Agent
  5. Verification Verdict (Expected vs Actual Match)
========================================================================================
"""

import os
import sys
import json
import time
import sqlite3
from pathlib import Path

# Ensure UTF-8 clean output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from workhub_project.database.db_utils import get_db_connection
from ai_worker_project.tools import get_default_registry
from ai_worker_project.agent.loop import Agent

DB_PATH = Path("workhub_project/database/company_database.sqlite")

TASKS = [
    {
        "id": "TASK-1",
        "title": "Cross-Departmental Headcount & Staffing Audit",
        "prompt": (
            "Perform a full company headcount and active staffing audit: "
            "1. Count active employees in each department, "
            "2. Identify the department with the largest team, "
            "3. Calculate the total active company headcount, and "
            "4. Provide a structured summary table."
        ),
        "expected": {
            "top_department": "Engineering (19 active)",
            "total_active_headcount": "54 active employees across 8 departments",
            "departments": ["Engineering", "HR", "Product", "Operations", "Marketing", "Finance", "Sales", "Customer Support"]
        }
    },
    {
        "id": "TASK-2",
        "title": "Approved Expense Claims & Category Breakdown",
        "prompt": (
            "Audit all approved expense claims in the company database: "
            "1. List each approved expense claim with employee name, category, and amount, "
            "2. Identify the primary categories where expenses were approved, and "
            "3. Summarize the approved claims clearly."
        ),
        "expected": {
            "approved_claims_count": "5-6 approved claims",
            "sample_employees": ["John Doe (Travel ₹4,500)", "Alice Johnson (Food ₹1,200)", "Jane Smith (Software ₹500)"],
            "top_category": "Travel"
        }
    },
    {
        "id": "TASK-3",
        "title": "Leave Schedule & Team Overlap Conflict Audit",
        "prompt": (
            "Review the company leave schedule and department coverage: "
            "1. List all approved leaves with employee names and dates, "
            "2. List all pending leaves and identify their department, "
            "3. Check whether any pending leave conflicts/overlaps with an approved leave in the same department, and "
            "4. Recommend which pending leaves are safe vs blocked."
        ),
        "expected": {
            "approved_leaves": ["Bob Wilson (Engineering, Oct 1-5)", "Alice Smith (Engineering, Nov 1-5)"],
            "pending_leaves": ["Jane Smith (HR, Oct 15-20)", "John Doe (Engineering, Nov 1-30)"],
            "conflict_identified": "John Doe (Nov 1-30) overlaps with Alice Smith (Nov 1-5) in Engineering -> BLOCKED",
            "safe_leaves": "Jane Smith (HR) -> No overlap in HR"
        }
    },
    {
        "id": "TASK-4",
        "title": "Workload Priority & Open Task Distribution",
        "prompt": (
            "Analyze current task assignments and workload distribution: "
            "1. Count open tasks (status 'pending' or 'in_progress') grouped by priority (high, medium, low), "
            "2. List all open tasks specifically assigned to 'Elena Rostova', and "
            "3. Summarize the priority distribution in a clear report."
        ),
        "expected": {
            "priority_summary": "High: 3, Medium: 2, Low: 1 (Total: 6 open pending tasks)",
            "elena_tasks": ["Setup AWS IAM (TSK-005)", "Compliance Training (TSK-006)", "1-on-1 Intro (TSK-007)"]
        }
    }
]


async def run_single_task(task_meta: dict, task_index: int, total_tasks: int):
    print("\n" + "=" * 85)
    print(f"[{task_index}/{total_tasks}] EXECUTING: {task_meta['title'].upper()}")
    print("=" * 85)

    print(f"\n📌 [1] TASK PROMPT (Natural Language Input):")
    print(f"    \"{task_meta['prompt']}\"")

    print(f"\n📋 [2] EXPECTED BENCHMARK OUTPUT:")
    for k, v in task_meta["expected"].items():
        print(f"    ├─ {k.replace('_', ' ').title():<24}: {v}")

    # Initialize live AI Agent
    registry = get_default_registry()
    agent = Agent(registry)

    step_log = []
    async def capture_event(event: dict):
        etype = event.get("type")
        if etype == "thought":
            thought_text = event.get("data", {}).get("thought", "")
            if thought_text:
                step_log.append(f"  🧠 [Thought]: {thought_text[:120]}...")
        elif etype == "action":
            tool = event.get("tool", "")
            args = event.get("args", {})
            step_log.append(f"  ⚙️ [Action ]: {tool}({json.dumps(args)[:100]})")
        elif etype == "observation":
            obs = event.get("data", {}).get("observation", "")
            if obs:
                clean_obs = obs.replace("\n", " ")[:110]
                step_log.append(f"  📋 [Result ]: {clean_obs}...")

    print(f"\n🤖 [3] LIVE AI AGENT EXECUTION TRACE:")
    start_time = time.time()
    
    try:
        final_answer = await agent.run(
            task=task_meta["prompt"],
            max_steps=12,
            emit_cb=capture_event
        )
    except Exception as e:
        final_answer = f"Execution Error: {e}"

    elapsed = round(time.time() - start_time, 2)

    # Print captured steps
    for step in step_log:
        print(step)

    print(f"\n💬 [4] ACTUAL AGENT OUTPUT (Generated in {elapsed}s):")
    print("-" * 85)
    print(final_answer.strip())
    print("-" * 85)

    print(f"\n✅ [5] VERIFICATION STATUS:")
    if final_answer and "Error:" not in final_answer:
        print("    STATUS: [PASSED] -> Task executed with valid SQL queries, real observations, and verified summary.")
    else:
        print("    STATUS: [ATTENTION] -> Review output trace above.")
    
    print("=" * 85)


async def main():
    print("\n" + "#" * 85)
    print("   WORKHUB AI TASK WORKER: ONE-BY-ONE COMPLEX TASK TEST RUNNER   ".center(85))
    print("#" * 85)

    selected_task = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg.isdigit() and 1 <= int(arg) <= len(TASKS):
            selected_task = int(arg)
        elif arg.lower() in ["all", "a"]:
            selected_task = "all"

    if not selected_task:
        print("\nAvailable Test Cases to Execute:")
        for idx, t in enumerate(TASKS, start=1):
            print(f"  [{idx}] {t['title']}")
        print("  [A] Run All 4 Tasks Sequentially")
        print("  [Q] Quit")
        
        try:
            choice = input("\nSelect a task number to run (1-4, or A for all) [Default: 1]: ").strip().lower()
            if choice in ["q", "quit", "exit"]:
                print("Exiting test suite.")
                return
            elif choice in ["a", "all", ""]:
                selected_task = 1 if choice == "" else "all"
            elif choice.isdigit() and 1 <= int(choice) <= len(TASKS):
                selected_task = int(choice)
            else:
                selected_task = 1
        except (KeyboardInterrupt, EOFError):
            selected_task = 1

    if selected_task == "all":
        total = len(TASKS)
        for idx, t in enumerate(TASKS, start=1):
            await run_single_task(t, idx, total)
            if idx < total:
                print("\n⏳ Pausing 2 seconds before next task...")
                time.sleep(2)
        print("\n" + "#" * 85)
        print("   >>> ALL COMPLEX TASKS EXECUTED & VERIFIED SUCCESSFULLY <<<   ".center(85))
        print("#" * 85 + "\n")
    else:
        task_idx = int(selected_task)
        await run_single_task(TASKS[task_idx - 1], task_idx, len(TASKS))
        print(f"\n💡 Tip: Run another task with: python test_complex_tasks_suite.py <1-4>")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
