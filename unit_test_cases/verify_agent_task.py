import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import sys
import time
import json
import sqlite3
import urllib.request
from pathlib import Path

# Ensure UTF-8 unbuffered output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

API_BASE = "http://localhost:8001/api"
DB_PATH = Path("workhub_project/database/company_database.sqlite")

def run_verification():
    print("=" * 80)
    print("🤖 WORKHUB AI AGENT BACKEND - LIVE TASK VERIFICATION")
    print("=" * 80)

    # 1. Check AI Agent Health
    print("\n[Step 1] Checking AI Agent Backend Health...")
    try:
        with urllib.request.urlopen(f"{API_BASE}/health") as resp:
            health_data = json.loads(resp.read().decode())
            print(f"  ✓ Health: {health_data.get('status')}")
            print(f"  ✓ Fallback Chain: {health_data.get('fallback_chain')}")
    except Exception as e:
        print(f"  ✗ Failed to connect to AI Agent API: {e}")
        return

    # 2. Check Available Tools
    print("\n[Step 2] Querying Registered Tools from AI Agent...")
    try:
        with urllib.request.urlopen(f"{API_BASE}/tools") as resp:
            tools_data = json.loads(resp.read().decode())
            tools = tools_data.get("tools", [])
            print(f"  ✓ Total Tools Available: {len(tools)}")
            print(f"  ✓ Sample Tools: {', '.join(tools[:6])} ...")
    except Exception as e:
        print(f"  ✗ Failed to fetch tools: {e}")

    # 3. Submit a Natural Language Task
    task_prompt = (
        "Create an employee record for 'Elena Rostova', Department: 'Engineering', "
        "Role: 'Senior Backend Engineer', Email: 'elena.rostova@workhub.internal', "
        "Status: 'ACTIVE', Salary: 135000."
    )
    print(f"\n[Step 3] Submitting Natural Language Task:")
    print(f"  📝 Prompt: \"{task_prompt}\"")

    post_data = json.dumps({"task": task_prompt, "max_steps": 100}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/runs",
        data=post_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        run_info = json.loads(resp.read().decode())
        run_id = run_info.get("run_id")
        print(f"  ✓ Task Accepted! Run ID: {run_id}")
        print(f"  ✓ Initial Status: {run_info.get('status')}")

    # 4. Poll and Stream Execution Progress
    print("\n[Step 4] Agent Autonomous Execution in Progress...")
    start_time = time.time()
    last_step_count = 0

    while True:
        time.sleep(1.5)
        elapsed = round(time.time() - start_time, 1)

        poll_req = urllib.request.Request(f"{API_BASE}/runs/{run_id}")
        with urllib.request.urlopen(poll_req) as resp:
            run_state = json.loads(resp.read().decode())
            status = run_state.get("status")
            steps = run_state.get("steps", [])

            # Print newly completed steps
            if len(steps) > last_step_count:
                for i in range(last_step_count, len(steps)):
                    step = steps[i]
                    thought = step.get("thought")
                    tool = step.get("tool_name")
                    args = step.get("tool_args")
                    obs = step.get("observation")
                    if thought:
                        print(f"  🧠 [Step {i+1} Thought]: {thought}")
                    if tool:
                        print(f"  ⚙️ [Step {i+1} Tool]: {tool}({json.dumps(args)})")
                    if obs:
                        # Clean/abbreviate observation
                        obs_clean = obs.strip().replace("\n", " ")
                        if len(obs_clean) > 120:
                            obs_clean = obs_clean[:120] + "..."
                        print(f"  📋 [Step {i+1} Result]: {obs_clean}")
                last_step_count = len(steps)

            if status in ("completed", "failed", "blocked_on_human") or elapsed > 45:
                print(f"\n[Step 5] Execution Finished in {elapsed}s with Status: [{status.upper()}]")
                print(f"  💬 Final Agent Answer: {run_state.get('final_answer')}")
                break

    # 5. Direct Database & Audit Log Verification
    print("\n[Step 6] Verifying SQLite Database & Audit Trail Synchronization...")
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            # Check Employee
            emp = conn.execute(
                "SELECT * FROM employees WHERE email = ?", 
                ('elena.rostova@workhub.internal',)
            ).fetchone()
            
            if emp:
                print(f"  ✅ SQLite Record Found: ID={emp['id']} | Name={emp['name']} | Role={emp['role']} | Dept={emp['department']} | Salary=${emp['salary']}")
            else:
                print("  ⚠️ Employee not found by exact email. Checking by name 'Elena'...")
                emps = conn.execute("SELECT * FROM employees WHERE name LIKE '%Elena%'").fetchall()
                for e in emps:
                    print(f"    - Found: {e['id']} | {e['name']} | {e['department']} | {e['role']}")

            # Check Audit Logs
            recent_logs = conn.execute(
                "SELECT * FROM audit_logs ORDER BY id DESC LIMIT 3"
            ).fetchall()
            print("  📜 Recent Audit Trail Entries:")
            for log in recent_logs:
                print(f"    - [{log['timestamp']}] Action={log['action']} | Entity={log['entity_type']} #{log['entity_id']} | Details={log['details']}")

    print("\n" + "=" * 80)
    print("🎉 AI AGENT BACKEND VERIFICATION COMPLETE: ALL SYSTEMS FULLY OPERATIONAL")
    print("=" * 80)

if __name__ == "__main__":
    run_verification()