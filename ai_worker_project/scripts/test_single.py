import asyncio
import sys
import logging
from ai_worker_project.agent.orchestrator import Orchestrator
from ai_worker_project.tools import get_default_registry
from ai_worker_project.agent.models import Run

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

logging.basicConfig(level=logging.INFO)

async def run_single():
    query = sys.argv[1]
    print(f"=== TESTING EDGE CASE ===")
    print(f"Task: {query}\n")
    
    registry = get_default_registry()
    orchestrator = Orchestrator(registry)
    run = Run(task_description=query)
    
    completed_run = await orchestrator.execute_run(run)
    
    print(f"\n=== RESULT ===")
    print(f"Status: {completed_run.status}")
    print(f"Final Answer: {completed_run.final_answer}")

if __name__ == "__main__":
    asyncio.run(run_single())
import asyncio
import sys
import logging
from ai_worker_project.agent.orchestrator import Orchestrator
from ai_worker_project.tools import get_default_registry
from ai_worker_project.agent.models import Run

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

logging.basicConfig(level=logging.INFO)

async def run_single():
    query = sys.argv[1]
    print(f"=== TESTING EDGE CASE ===")
    print(f"Task: {query}\n")
    
    registry = get_default_registry()
    orchestrator = Orchestrator(registry)
    run = Run(task_description=query)
    
    completed_run = await orchestrator.execute_run(run)
    
    print(f"\n=== RESULT ===")
    print(f"Status: {completed_run.status}")
    print(f"Final Answer: {completed_run.final_answer}")

if __name__ == "__main__":
    asyncio.run(run_single())
