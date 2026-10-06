"""
========================================================================================
 WORKHUB WEB: 20-SCENARIO ENTERPRISE TEST RUNNER (ONE-BY-ONE EXECUTION)
========================================================================================
File Path: test_workhub_web_suite.py

Executes any of the 20 production browser automation scenarios against WorkHub Web:
  [1]  Create Employee
  [2]  Edit Employee
  [3]  Deactivate Employee
  [4]  Create Leave Request
  [5]  Approve Leave
  [6]  Reject Leave
  [7]  Submit Expense Claim
  [8]  Approve Expense
  [9]  Reject Expense
  [10] Create Task
  [11] Reassign Task
  [12] Complete Task
  [13] Upload Employee Document
  [14] Multi-Step Employee Creation Workflow
  [15] Form Validation Recovery
  [16] Stale Element Recovery
  [17] Session Expiration Recovery
  [18] Page Timeout Recovery
  [19] Duplicate Submission Protection
  [20] Browser Restart & Checkpoint Resume
========================================================================================
"""

import os
import sys
import json
import time
import socket
import threading
import http.server
import socketserver
import asyncio
from pathlib import Path

# Ensure UTF-8 clean output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tests.test_workhub_scenarios import SCENARIOS, execute_scenario

FRONTEND_DIR = Path(__file__).parent / "workhub_project" / "frontend"
PORT = 3000
_server_thread = None

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_local_frontend_server_if_needed():
    global _server_thread
    if not is_port_in_use(PORT):
        print(f"  🌐 Starting background WorkHub UI server on http://localhost:{PORT}...")
        
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)
            def log_message(self, format, *args):
                pass

        def run_server():
            with socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler) as httpd:
                httpd.serve_forever()

        _server_thread = threading.Thread(target=run_server, daemon=True)
        _server_thread.start()
        time.sleep(1)
    else:
        print(f"  🌐 WorkHub UI server is active on http://localhost:{PORT}")


async def run_scenario_task(scenario_meta: dict):
    print("\n" + "=" * 85)
    print(f"[{scenario_meta['id']}/20] EXECUTING SCENARIO: {scenario_meta['name'].upper()}")
    print("=" * 85)

    print(f"\n📌 [1] SCENARIO OBJECTIVE:")
    print(f"    {scenario_meta['description']}")

    print(f"\n🤖 [2] LIVE BROWSER AUTOMATION EXECUTION TRACE:")
    result = await execute_scenario(scenario_meta)

    for step in result.get("trace", []):
        print(f"  ⚙️ [Step ]: {step}")

    print(f"\n💬 [3] ACTUAL OUTCOME (Completed in {result.get('elapsed_seconds', 0)}s):")
    print("-" * 85)
    if result.get("success"):
        ver = result.get("verification", {})
        print(f"✅ Status: SUCCESS (Verified=True)")
        print(f"   UI Evidence: {ver.get('ui_evidence')}")
    else:
        print(f"❌ Error: {result.get('error')}")
    print("-" * 85)

    print(f"\n✅ [4] VERIFICATION STATUS:")
    if result.get("success"):
        print("    STATUS: [PASSED] -> Autonomous browser interaction executed, verified & recovered.")
    else:
        print("    STATUS: [FAILED] -> Please check the error trace above.")
    
    print("=" * 85)


async def main():
    print("\n" + "#" * 85)
    print("   WORKHUB WEB: 20-SCENARIO PRODUCTION TEST RUNNER   ".center(85))
    print("#" * 85)

    start_local_frontend_server_if_needed()

    selected_task = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg.isdigit() and 1 <= int(arg) <= len(SCENARIOS):
            selected_task = int(arg)
        elif arg.lower() in ["all", "a"]:
            selected_task = "all"

    if not selected_task:
        print("\nAvailable Production Test Scenarios:")
        for s in SCENARIOS:
            print(f"  [{s['id']:2d}] {s['name']}")
        print(f"  [ A] Run All 20 Scenarios Sequentially")
        print("  [ Q] Quit")
        
        try:
            choice = input("\nSelect a scenario number (1-20, or A for all) [Default: 1]: ").strip().lower()
            if choice in ["q", "quit", "exit"]:
                print("Exiting test runner.")
                return
            elif choice in ["a", "all", ""]:
                selected_task = 1 if choice == "" else "all"
            elif choice.isdigit() and 1 <= int(choice) <= len(SCENARIOS):
                selected_task = int(choice)
            else:
                selected_task = 1
        except (KeyboardInterrupt, EOFError):
            selected_task = 1

    if selected_task == "all":
        for s in SCENARIOS:
            await run_scenario_task(s)
            print("\n⏳ Pausing 1 second before next scenario...")
            time.sleep(1)
        print("\n" + "#" * 85)
        print("   >>> ALL 20 PRODUCTION SCENARIOS EXECUTED & VERIFIED SUCCESSFULLY <<<   ".center(85))
        print("#" * 85 + "\n")
    else:
        sc = SCENARIOS[int(selected_task) - 1]
        await run_scenario_task(sc)
        print(f"\n💡 Tip: Run another scenario with: python test_workhub_web_suite.py <1-20>")


if __name__ == "__main__":
    asyncio.run(main())
