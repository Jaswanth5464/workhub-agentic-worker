"""
========================================================================================
 WORKHUB AI TASK WORKER: NATURAL LANGUAGE BROWSER RUNNER
========================================================================================
File Path: agent_nlp_browser_runner.py

This script allows you to execute ANY Natural Language command against the live
AI Task Worker agent.

For every command:
  1. It launches a fresh, visible Chromium browser window on your screen.
  2. The AI Agent reads your plain English request, reasons with the LLM, and plans actions.
  3. The Agent executes browser actions live (clicks, fills, navigates, observes, recovers).
  4. It prints the live thought trace, actions, and verified final answer.
========================================================================================
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import os
import sys
import time
import json
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

from dotenv import load_dotenv
load_dotenv()

# Force headed visible browser so user can see Chromium open on screen
os.environ["HEADLESS"] = "false"

from ai_worker_project.tools import get_default_registry
from ai_worker_project.agent.loop import Agent
from ai_worker_project.tools.browser import close_browser_session

FRONTEND_DIR = Path(__file__).parent / "workhub_project" / "frontend"
PORT = 3000
_server_thread = None

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_local_frontend_server_if_needed():
    global _server_thread
    if not is_port_in_use(PORT):
        print(f"🌐 Starting background WorkHub UI server on http://localhost:{PORT}...")
        
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
        print(f"🌐 WorkHub UI is active on http://localhost:{PORT}")


SAMPLE_NLP_COMMANDS = [
    "Open http://localhost:3000/index.html, observe the page, and tell me all the available navigation tabs.",
    "Go to the Employees directory at http://localhost:3000/index.html, search for 'Engineering', and summarize who you find.",
    "Navigate to http://localhost:3000/index.html, switch to the Expenses view, and verify if there are any pending claims.",
    "Open http://localhost:3000/index.html, click on Tasks, and create a new task titled 'Review Cloud Security' assigned to 'Admin'.",
    "Open http://localhost:3000/index.html, take a full-page screenshot of the dashboard, and tell me the file path where it was saved."
]


async def run_nlp_task(user_prompt: str):
    print("\n" + "=" * 85)
    print("🤖 EXECUTING NATURAL LANGUAGE AI BROWSER TASK".center(85))
    print("=" * 85)
    print(f"\n📝 YOUR NLP COMMAND:")
    print(f"   \"{user_prompt}\"")

    print(f"\n🚀 Launching fresh Chromium browser window on your desktop...")
    
    # Generate unique run ID so a brand new session opens every time
    run_id = f"nlp_run_{int(time.time()*1000)}"
    registry = get_default_registry()
    agent = Agent(registry)

    step_log = []
    async def capture_event(event: dict):
        etype = event.get("type")
        if etype == "thought":
            thought_text = event.get("data", {}).get("thought", "")
            if thought_text:
                print(f"  🧠 [AI Thought]: {thought_text[:140]}...")
        elif etype == "action":
            tool = event.get("tool", "")
            args = event.get("args", {})
            print(f"  ⚙️ [AI Action ]: {tool}({json.dumps(args)[:100]})")
        elif etype == "observation":
            obs = event.get("data", {}).get("observation", "")
            if obs:
                clean_obs = obs.replace("\n", " ")[:120]
                print(f"  📋 [Browser Obs]: {clean_obs}...")

    start_time = time.time()
    try:
        final_answer = await agent.run(
            task=user_prompt,
            max_steps=100,
            emit_cb=capture_event,
            run_id=run_id
        )
    except Exception as e:
        final_answer = f"Execution Error: {e}"

    elapsed = round(time.time() - start_time, 2)

    print("\n" + "-" * 85)
    print(f"💬 FINAL AGENT ANSWER (Completed in {elapsed}s):")
    print("-" * 85)
    print(final_answer.strip())
    print("-" * 85)

    # Keep browser open for inspection
    print("\n👀 Keeping Chromium window open for 5 seconds so you can see the result...")
    await asyncio.sleep(5)

    # Clean up browser session
    await close_browser_session(run_id)
    print("🔒 Chromium browser session closed cleanly.\n")


async def main():
    print("\n" + "#" * 85)
    print("   WORKHUB AI TASK WORKER: NATURAL LANGUAGE BROWSER AUTOMATION CONSOLE   ".center(85))
    print("#" * 85)

    start_local_frontend_server_if_needed()

    if len(sys.argv) > 1:
        custom_prompt = " ".join(sys.argv[1:]).strip()
        await run_nlp_task(custom_prompt)
        return

    while True:
        print("\nChoose an option:")
        for idx, cmd in enumerate(SAMPLE_NLP_COMMANDS, start=1):
            print(f"  [{idx}] {cmd}")
        print("  [C] Enter your own Custom Natural Language Command")
        print("  [Q] Quit\n")

        try:
            choice = input("Select an option (1-5, C, or Q) [Default: 1]: ").strip().lower()
            if choice in ["q", "quit", "exit"]:
                print("Exiting.")
                break
            elif choice == "c":
                custom = input("\nType your Natural Language task for the AI Agent: ").strip()
                if custom:
                    await run_nlp_task(custom)
            elif choice.isdigit() and 1 <= int(choice) <= len(SAMPLE_NLP_COMMANDS):
                await run_nlp_task(SAMPLE_NLP_COMMANDS[int(choice) - 1])
            elif choice in ["", "1"]:
                await run_nlp_task(SAMPLE_NLP_COMMANDS[0])
            else:
                print("Invalid option. Please choose 1-5, C, or Q.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break


if __name__ == "__main__":
    asyncio.run(main())
